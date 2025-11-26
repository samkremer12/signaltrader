"""
Periodic Celery tasks for SignalTrader
- Trailing stop-loss monitoring
- Position monitoring
- System health checks
"""
from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime
import ccxt
import logging

from app.db import SessionLocal
from app.models import Position, Settings, Trade, User
from app.security import decrypt_api_key

logger = logging.getLogger(__name__)


@shared_task(name="monitor_trailing_stops")
def monitor_trailing_stops():
    """
    Monitor all open positions with trailing stop-loss enabled.
    This task runs periodically (every 30 seconds) to check if trailing stops need adjustment.
    """
    db = SessionLocal()
    try:
        # Get all users with trailing stop-loss enabled
        users_with_trailing = db.query(User).join(Settings).filter(
            Settings.trailing_stop_enabled == True
        ).all()
        
        logger.info(f"Monitoring trailing stops for {len(users_with_trailing)} users")
        
        for user in users_with_trailing:
            settings = db.query(Settings).filter(Settings.user_id == user.id).first()
            if not settings or not settings.trailing_stop_enabled:
                continue
            
            # Get all open positions for this user
            positions = db.query(Position).filter(
                Position.user_id == user.id,
                Position.status == "open"
            ).all()
            
            for position in positions:
                try:
                    # Get current market price
                    exchange_class = getattr(ccxt, position.exchange)
                    exchange = exchange_class({'enableRateLimit': True})
                    ticker = exchange.fetch_ticker(position.symbol)
                    current_price = float(ticker['last'])
                    
                    # Update highest price if current price is higher
                    if position.highest_price is None or current_price > position.highest_price:
                        position.highest_price = current_price
                        logger.info(f"Updated highest price for {position.symbol}: {current_price}")
                    
                    # Calculate trailing stop price
                    trailing_percent = settings.trailing_stop_percent or 1.0
                    trailing_stop_price = position.highest_price * (1 - trailing_percent / 100)
                    
                    # Update trailing stop price
                    position.trailing_stop_price = trailing_stop_price
                    
                    # Check if current price hit the trailing stop
                    if current_price <= trailing_stop_price:
                        logger.info(f"Trailing stop hit for {position.symbol} at {current_price}")
                        
                        # Close the position
                        from app.tasks.trading_tasks import close_position_task
                        close_position_task.delay(
                            user_id=str(user.id),
                            symbol=position.symbol,
                            exchange_name=position.exchange
                        )
                        
                        # Add trade log
                        trade = Trade(
                            user_id=user.id,
                            symbol=position.symbol,
                            action="sell",
                            price=current_price,
                            size=position.size,
                            exchange=position.exchange,
                            result=f"Trailing stop-loss triggered at {current_price}",
                            timestamp=datetime.utcnow(),
                            is_paper_trade=False,
                            fees=position.size * current_price * 0.001
                        )
                        db.add(trade)
                    
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Error monitoring trailing stop for {position.symbol}: {str(e)}")
                    db.rollback()
                    continue
        
        return {"status": "success", "users_monitored": len(users_with_trailing)}
        
    except Exception as e:
        logger.error(f"Error in monitor_trailing_stops: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@shared_task(name="send_trade_notification")
def send_trade_notification(user_id: str, trade_type: str, symbol: str, price: float, size: float):
    """
    Send email notification for trade execution.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        settings = db.query(Settings).filter(Settings.user_id == user_id).first()
        if not settings or not settings.enable_notifications or not settings.notification_email:
            return {"status": "skipped", "message": "Notifications not enabled"}
        
        # Send email notification
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import os
        
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        
        if not smtp_user or not smtp_password:
            logger.warning("SMTP credentials not configured, skipping email notification")
            return {"status": "skipped", "message": "SMTP not configured"}
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = settings.notification_email
        msg['Subject'] = f"SignalTrader: {trade_type.upper()} {symbol}"
        
        body = f"""
        Trade Executed on SignalTrader
        
        Type: {trade_type.upper()}
        Symbol: {symbol}
        Price: ${price:.2f}
        Size: {size}
        Total: ${price * size:.2f}
        
        Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        
        This is an automated notification from SignalTrader.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent to {settings.notification_email}")
            return {"status": "success", "message": "Email sent"}
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {"status": "error", "message": str(e)}
        
    except Exception as e:
        logger.error(f"Error in send_trade_notification: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@shared_task(name="system_health_check")
def system_health_check():
    """
    Periodic system health check to monitor platform status.
    """
    db = SessionLocal()
    try:
        from app.models import SystemHealth
        
        # Count active users (users with trades in last 24 hours)
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        active_users = db.query(User).join(Trade).filter(
            Trade.timestamp >= yesterday
        ).distinct().count()
        
        # Count trades in last 24 hours
        trades_24h = db.query(Trade).filter(
            Trade.timestamp >= yesterday
        ).count()
        
        # Count open positions
        open_positions = db.query(Position).filter(
            Position.status == "open"
        ).count()
        
        # Create health record
        health = SystemHealth(
            active_users=active_users,
            trades_24h=trades_24h,
            open_positions=open_positions,
            celery_status="running",
            timestamp=datetime.utcnow()
        )
        db.add(health)
        db.commit()
        
        logger.info(f"System health check: {active_users} active users, {trades_24h} trades (24h), {open_positions} open positions")
        
        return {
            "status": "success",
            "active_users": active_users,
            "trades_24h": trades_24h,
            "open_positions": open_positions
        }
        
    except Exception as e:
        logger.error(f"Error in system_health_check: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

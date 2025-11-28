from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import User, ApiCredential, Trade, Log, Settings, Position
from app.security import decrypt_api_key
import ccxt
from datetime import datetime
import traceback
import json

@celery_app.task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True, retry_jitter=True)
def execute_order_task(self, user_id: int, symbol: str, side: str, size: float, price: float = None, exchange_name: str = "binance"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if paper trading is enabled
        settings = db.query(Settings).filter(Settings.user_id == user_id).first()
        if not settings:
            settings = Settings(user_id=user_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        is_paper_trade = settings.paper_trading_enabled
        
        # Check for existing position to enforce buy->sell->buy->sell pattern
        position = db.query(Position).filter(
            Position.user_id == user_id,
            Position.symbol == symbol,
            Position.is_open == True
        ).first()
        
        # Enforce alternating buy/sell pattern
        if side.lower() == 'buy' and position:
            # Already have an open position, reject duplicate buy
            log = Log(
                user_id=user_id,
                level="warning",
                message=f"REJECTED: Buy signal ignored - already have open position for {symbol}",
                data=json.dumps({"rejected_side": "buy", "existing_position": True, "task_id": self.request.id}),
                timestamp=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            return {
                "success": False,
                "error": "Already have open position",
                "message": f"Buy signal rejected - already holding {symbol}. Must sell first."
            }
        
        if side.lower() == 'sell' and not position:
            # No open position to sell, reject
            log = Log(
                user_id=user_id,
                level="warning",
                message=f"REJECTED: Sell signal ignored - no open position for {symbol}",
                data=json.dumps({"rejected_side": "sell", "existing_position": False, "task_id": self.request.id}),
                timestamp=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            return {
                "success": False,
                "error": "No open position",
                "message": f"Sell signal rejected - no position to sell for {symbol}. Must buy first."
            }
        
        if is_paper_trade:
            # Paper trading mode - simulate the trade
            # Use price from webhook, or default to a reasonable value if not provided
            if price is None:
                raise ValueError("Price is required for paper trading mode")
            simulated_price = float(price)
            
            trade = Trade(
                user_id=user_id,
                symbol=symbol,
                action=side,
                price=float(simulated_price),
                size=size,
                exchange=exchange_name,
                result=f"PAPER TRADE - Simulated: {side} {size} {symbol}",
                timestamp=datetime.utcnow(),
                is_paper_trade=True,
                fees=0.0
            )
            db.add(trade)
            
            # Create or close position for paper trading
            if side.lower() == 'buy':
                # Create new position (we already checked no position exists)
                position = Position(
                    user_id=user_id,
                    symbol=symbol,
                    side="LONG",
                    entry_price=simulated_price,
                    size=size,
                    initial_size=size,
                    highest_price=simulated_price
                )
                db.add(position)
            elif side.lower() == 'sell':
                # Close existing position (we already checked position exists)
                if position:
                    position.is_open = False
                    position.exit_price = simulated_price
                    position.pnl = (simulated_price - position.entry_price) * position.size
            
            log = Log(
                user_id=user_id,
                level="info",
                message=f"PAPER TRADE - Order simulated: {side} {size} {symbol} at {simulated_price}",
                data=json.dumps({"simulated_price": simulated_price, "task_id": self.request.id}),
                timestamp=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            
            # Send email notification if enabled
            from app.tasks.periodic_tasks import send_trade_notification
            send_trade_notification.delay(str(user_id), side, symbol, float(simulated_price), size)
            
            return {
                "success": True,
                "order_id": f"paper_{self.request.id}",
                "trade_id": trade.id,
                "message": f"Successfully simulated {side} order for {symbol} (PAPER TRADE)",
                "is_paper_trade": True
            }
        else:
            # Real trading mode - execute on exchange
            api_cred = db.query(ApiCredential).filter(
                ApiCredential.user_id == user_id,
                ApiCredential.exchange_name == exchange_name
            ).first()
            
            if not api_cred:
                raise ValueError(f"No API credentials found for exchange {exchange_name}")
            
            api_key = decrypt_api_key(api_cred.encrypted_api_key)
            api_secret = decrypt_api_key(api_cred.encrypted_api_secret)
            
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            
            order_type = 'market' if price is None else 'limit'
            order = exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=size,
                price=price
            )
            
            # Calculate fees (estimate 0.1% for most exchanges)
            executed_price = float(order.get('price', price or 0))
            fees = executed_price * size * 0.001
            
            trade = Trade(
                user_id=user_id,
                symbol=symbol,
                action=side,
                price=executed_price,
                size=size,
                exchange=exchange_name,
                result=f"Success: {order.get('id', 'unknown')}",
                order_id=order.get('id'),
                timestamp=datetime.utcnow(),
                is_paper_trade=False,
                fees=fees
            )
            db.add(trade)
            
            # Create or close position for live trading
            if side.lower() == 'buy':
                # Create new position (we already checked no position exists)
                position = Position(
                    user_id=user_id,
                    symbol=symbol,
                    side="LONG",
                    entry_price=executed_price,
                    size=size,
                    initial_size=size,
                    highest_price=executed_price
                )
                db.add(position)
            elif side.lower() == 'sell':
                # Close existing position (we already checked position exists)
                if position:
                    position.is_open = False
                    position.exit_price = executed_price
                    position.pnl = (executed_price - position.entry_price) * position.size
            
            log = Log(
                user_id=user_id,
                level="info",
                message=f"Order executed: {side} {size} {symbol} at {order.get('price', price)}",
                data=json.dumps({"order": str(order), "task_id": self.request.id}),
                timestamp=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            
            return {
                "success": True,
                "order_id": order.get('id'),
                "trade_id": trade.id,
                "message": f"Successfully executed {side} order for {symbol}"
            }
        
    except Exception as e:
        error_msg = f"Failed to execute order: {str(e)}"
        traceback_str = traceback.format_exc()
        
        log = Log(
            user_id=user_id,
            level="error",
            message=error_msg,
            data=json.dumps({"error": str(e), "traceback": traceback_str, "task_id": self.request.id}),
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        
        return {
            "success": False,
            "error": error_msg,
            "message": f"Failed to execute {side} order for {symbol} after {self.max_retries} retries"
        }
    finally:
        db.close()

@celery_app.task(bind=True, autoretry_for=(Exception,), max_retries=3, retry_backoff=True, retry_jitter=True)
def close_position_task(self, user_id: int, symbol: str, exchange_name: str = "binance"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        api_cred = db.query(ApiCredential).filter(
            ApiCredential.user_id == user_id,
            ApiCredential.exchange_name == exchange_name
        ).first()
        
        if not api_cred:
            raise ValueError(f"No API credentials found for exchange {exchange_name}")
        
        api_key = decrypt_api_key(api_cred.encrypted_api_key)
        api_secret = decrypt_api_key(api_cred.encrypted_api_secret)
        
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        balance = exchange.fetch_balance()
        positions = balance.get('info', {}).get('positions', [])
        
        closed_orders = []
        for position in positions:
            if position.get('symbol') == symbol and float(position.get('positionAmt', 0)) != 0:
                side = 'sell' if float(position['positionAmt']) > 0 else 'buy'
                amount = abs(float(position['positionAmt']))
                
                order = exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side,
                    amount=amount
                )
                closed_orders.append(order)
                
                trade = Trade(
                    user_id=user_id,
                    symbol=symbol,
                    action='close',
                    price=float(order.get('price', 0)),
                    size=amount,
                    exchange=exchange_name,
                    result=f"Closed: {order.get('id', 'unknown')}",
                    timestamp=datetime.utcnow()
                )
                db.add(trade)
        
        log = Log(
            user_id=user_id,
            level="info",
            message=f"Position closed for {symbol}",
            data=json.dumps({"orders": str(closed_orders), "task_id": self.request.id}),
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        return {
            "success": True,
            "closed_orders": len(closed_orders),
            "message": f"Successfully closed position for {symbol}"
        }
        
    except Exception as e:
        error_msg = f"Failed to close position: {str(e)}"
        traceback_str = traceback.format_exc()
        
        log = Log(
            user_id=user_id,
            level="error",
            message=error_msg,
            data=json.dumps({"error": str(e), "traceback": traceback_str, "task_id": self.request.id}),
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        
        return {
            "success": False,
            "error": error_msg,
            "message": f"Failed to close position for {symbol} after {self.max_retries} retries"
        }
    finally:
        db.close()

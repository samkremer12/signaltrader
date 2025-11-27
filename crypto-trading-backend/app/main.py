from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import ccxt
import logging
import json
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sentry_sdk

from app.db import engine, Base, get_db
from app import models, schemas, security
from app.tasks.trading_tasks import execute_order_task, close_position_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Sentry for error reporting (Phase 2)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )
    logger.info("Sentry error reporting initialized")
else:
    logger.info("Sentry DSN not configured, skipping error reporting")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SignalTrader API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = security.decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def get_user_api_credential(user: models.User, db: Session) -> Optional[models.ApiCredential]:
    return db.query(models.ApiCredential).filter(models.ApiCredential.user_id == user.id).first()

def get_user_settings(user: models.User, db: Session) -> models.Settings:
    settings = db.query(models.Settings).filter(models.Settings.user_id == user.id).first()
    if not settings:
        settings = models.Settings(user_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

def add_user_log(user: models.User, db: Session, level: str, message: str, data: Optional[dict] = None):
    log = models.Log(user_id=user.id, level=level, message=message, data=json.dumps(data) if data else None)
    db.add(log)
    db.commit()
    logger.info(f"[{user.username}] [{level}] {message}")

def get_exchange(user: models.User, db: Session):
    api_cred = get_user_api_credential(user, db)
    if not api_cred or not api_cred.encrypted_api_key or not api_cred.encrypted_api_secret:
        raise HTTPException(status_code=400, detail="API keys not configured")
    try:
        api_key = security.decrypt_api_key(api_cred.encrypted_api_key)
        api_secret = security.decrypt_api_key(api_cred.encrypted_api_secret)
        exchange_class = getattr(ccxt, api_cred.exchange_name)
        exchange = exchange_class({'apiKey': api_key, 'secret': api_secret, 'enableRateLimit': True})
        return exchange
    except Exception as e:
        add_user_log(user, db, "ERROR", f"Failed to initialize exchange: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize exchange: {str(e)}")

def test_exchange_connection(user: models.User, db: Session):
    try:
        exchange = get_exchange(user, db)
        balance = exchange.fetch_balance()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

@app.post("/register", response_model=schemas.Token)
@limiter.limit("5/minute")
async def register(request: Request, user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    user = models.User(username=user_data.username, password_hash=security.hash_password(user_data.password), is_admin=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    settings = models.Settings(user_id=user.id)
    db.add(settings)
    db.commit()
    access_token = security.create_access_token(data={"sub": user.id})
    logger.info(f"New user registered: {user.username}")
    return schemas.Token(access_token=access_token, token_type="bearer", user=schemas.UserOut.from_orm(user))

@app.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token = security.create_access_token(data={"sub": user.id})
    logger.info(f"User logged in: {user.username}")
    return schemas.Token(access_token=access_token, token_type="bearer", user=schemas.UserOut.from_orm(user))

@app.get("/me", response_model=schemas.UserOut)
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    return schemas.UserOut.from_orm(current_user)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/set-api-key", response_model=schemas.APIKeyResponse)
async def set_api_key(request: schemas.APIKeyRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        api_cred = get_user_api_credential(current_user, db)
        if not api_cred:
            api_cred = models.ApiCredential(user_id=current_user.id)
            db.add(api_cred)
        api_cred.encrypted_api_key = security.encrypt_api_key(request.api_key)
        api_cred.encrypted_api_secret = security.encrypt_api_key(request.api_secret)
        api_cred.exchange_name = request.exchange or "binance"
        db.commit()
        connected, message = test_exchange_connection(current_user, db)
        if connected:
            add_user_log(current_user, db, "INFO", f"API keys configured successfully for {api_cred.exchange_name}")
            return schemas.APIKeyResponse(success=True, message="API keys configured successfully", exchange=api_cred.exchange_name, connected=True)
        else:
            add_user_log(current_user, db, "WARNING", f"API keys set but connection test failed: {message}")
            return schemas.APIKeyResponse(success=True, message="API keys set but connection test failed", exchange=api_cred.exchange_name, connected=False, error=message)
    except Exception as e:
        add_user_log(current_user, db, "ERROR", f"Failed to set API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/{webhook_token}", response_model=schemas.WebhookResponse)
@limiter.limit("60/minute")
async def webhook(request: Request, webhook_token: str, webhook_data: schemas.WebhookRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.webhook_token == webhook_token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid webhook token")
    try:
        webhook_event = models.WebhookEvent(user_id=user.id, action=webhook_data.action, symbol=webhook_data.symbol, price=webhook_data.price)
        db.add(webhook_event)
        db.commit()
        add_user_log(user, db, "INFO", f"Webhook received: {webhook_data.action} {webhook_data.symbol} @ {webhook_data.price}")
        settings = get_user_settings(user, db)
        if not settings.auto_trading_enabled:
            add_user_log(user, db, "WARNING", "Auto-trading is disabled, ignoring webhook")
            return schemas.WebhookResponse(success=True, message="Webhook received but auto-trading is disabled", action=webhook_data.action)
        
        api_cred = get_user_api_credential(user, db)
        exchange_name = api_cred.exchange_name if api_cred else "binance"
        
        if webhook_data.action.lower() == "buy":
            task = execute_order_task.delay(user.id, webhook_data.symbol, "buy", webhook_data.size or settings.default_position_size, webhook_data.price, exchange_name)
            add_user_log(user, db, "INFO", f"Buy order enqueued: task_id={task.id}")
            return schemas.WebhookResponse(success=True, message=f"Buy order enqueued (task_id: {task.id})", action=webhook_data.action)
        elif webhook_data.action.lower() == "sell":
            task = execute_order_task.delay(user.id, webhook_data.symbol, "sell", webhook_data.size or settings.default_position_size, webhook_data.price, exchange_name)
            add_user_log(user, db, "INFO", f"Sell order enqueued: task_id={task.id}")
            return schemas.WebhookResponse(success=True, message=f"Sell order enqueued (task_id: {task.id})", action=webhook_data.action)
        elif webhook_data.action.lower() == "close":
            task = close_position_task.delay(user.id, webhook_data.symbol, exchange_name)
            add_user_log(user, db, "INFO", f"Close position enqueued: task_id={task.id}")
            return schemas.WebhookResponse(success=True, message=f"Close position enqueued (task_id: {task.id})", action=webhook_data.action)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {webhook_data.action}")
    except Exception as e:
        add_user_log(user, db, "ERROR", f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_buy(user: models.User, db: Session, symbol: str, size: Optional[float] = None):
    try:
        exchange = get_exchange(user, db)
        settings = get_user_settings(user, db)
        api_cred = get_user_api_credential(user, db)
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        if size is None:
            size = settings.default_position_size / current_price
        if settings.trading_mode == "market":
            order = exchange.create_market_buy_order(symbol, size)
        elif settings.trading_mode == "limit":
            limit_price = current_price * (1 - settings.slippage / 100)
            order = exchange.create_limit_buy_order(symbol, size, limit_price)
        else:
            try:
                order = exchange.create_market_buy_order(symbol, size)
            except:
                limit_price = current_price * (1 - settings.slippage / 100)
                order = exchange.create_limit_buy_order(symbol, size, limit_price)
        trade = models.Trade(user_id=user.id, action="BUY", symbol=symbol, price=order.get('price', current_price), size=size, exchange=api_cred.exchange_name, result="SUCCESS", order_id=order.get('id'), pnl=0.0)
        db.add(trade)
        position = db.query(models.Position).filter(models.Position.user_id == user.id, models.Position.symbol == symbol, models.Position.is_open == True).first()
        if not position:
            position = models.Position(user_id=user.id, symbol=symbol, side="LONG", entry_price=order.get('price', current_price), size=size)
            db.add(position)
        else:
            total_cost = (position.entry_price * position.size) + (order.get('price', current_price) * size)
            position.size += size
            position.entry_price = total_cost / position.size
        db.commit()
        add_user_log(user, db, "INFO", f"Buy order executed: {symbol} @ {order.get('price', current_price)}")
        return {"success": True, "message": "Buy order executed", "order": order}
    except Exception as e:
        add_user_log(user, db, "ERROR", f"Buy order failed: {str(e)}")
        trade = models.Trade(user_id=user.id, action="BUY", symbol=symbol, price=0, size=size or 0, exchange=api_cred.exchange_name if api_cred else "unknown", result=f"FAILED: {str(e)}", pnl=0.0)
        db.add(trade)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

async def execute_sell(user: models.User, db: Session, symbol: str, size: Optional[float] = None):
    try:
        exchange = get_exchange(user, db)
        settings = get_user_settings(user, db)
        api_cred = get_user_api_credential(user, db)
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        position = db.query(models.Position).filter(models.Position.user_id == user.id, models.Position.symbol == symbol, models.Position.is_open == True).first()
        if size is None and position:
            size = position.size
        elif size is None:
            size = settings.default_position_size / current_price
        if settings.trading_mode == "market":
            order = exchange.create_market_sell_order(symbol, size)
        elif settings.trading_mode == "limit":
            limit_price = current_price * (1 + settings.slippage / 100)
            order = exchange.create_limit_sell_order(symbol, size, limit_price)
        else:
            try:
                order = exchange.create_market_sell_order(symbol, size)
            except:
                limit_price = current_price * (1 + settings.slippage / 100)
                order = exchange.create_limit_sell_order(symbol, size, limit_price)
        pnl = 0
        if position:
            entry_price = position.entry_price
            exit_price = order.get('price', current_price)
            if position.side == "LONG":
                pnl = (exit_price - entry_price) * size
            else:
                pnl = (entry_price - exit_price) * size
            settings.total_pnl += pnl
            if size >= position.size:
                position.is_open = False
            else:
                position.size -= size
        trade = models.Trade(user_id=user.id, action="SELL", symbol=symbol, price=order.get('price', current_price), size=size, exchange=api_cred.exchange_name, result=f"SUCCESS (PnL: ${pnl:.2f})", order_id=order.get('id'), pnl=pnl)
        db.add(trade)
        db.commit()
        add_user_log(user, db, "INFO", f"Sell order executed: {symbol} @ {order.get('price', current_price)} (PnL: ${pnl:.2f})")
        return {"success": True, "message": "Sell order executed", "order": order, "pnl": pnl}
    except Exception as e:
        add_user_log(user, db, "ERROR", f"Sell order failed: {str(e)}")
        trade = models.Trade(user_id=user.id, action="SELL", symbol=symbol, price=0, size=size or 0, exchange=api_cred.exchange_name if api_cred else "unknown", result=f"FAILED: {str(e)}", pnl=0.0)
        db.add(trade)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

async def close_position(user: models.User, db: Session, symbol: str):
    position = db.query(models.Position).filter(models.Position.user_id == user.id, models.Position.symbol == symbol, models.Position.is_open == True).first()
    if not position:
        raise HTTPException(status_code=400, detail="No open position for this symbol")
    return await execute_sell(user, db, symbol, position.size)

@app.post("/place-order")
async def place_order(request: schemas.OrderRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        api_cred = get_user_api_credential(current_user, db)
        exchange_name = api_cred.exchange_name if api_cred else "binance"
        settings = get_user_settings(current_user, db)
        
        if request.side.lower() == "buy":
            task = execute_order_task.delay(current_user.id, request.symbol, "buy", request.amount or settings.default_position_size, None, exchange_name)
            add_user_log(current_user, db, "INFO", f"Buy order enqueued: task_id={task.id}")
            return {"success": True, "message": f"Buy order enqueued (task_id: {task.id})", "task_id": task.id}
        elif request.side.lower() == "sell":
            task = execute_order_task.delay(current_user.id, request.symbol, "sell", request.amount or settings.default_position_size, None, exchange_name)
            add_user_log(current_user, db, "INFO", f"Sell order enqueued: task_id={task.id}")
            return {"success": True, "message": f"Sell order enqueued (task_id: {task.id})", "task_id": task.id}
        else:
            raise HTTPException(status_code=400, detail="Side must be 'buy' or 'sell'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/close-order")
async def close_order(request: schemas.CloseOrderRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    api_cred = get_user_api_credential(current_user, db)
    exchange_name = api_cred.exchange_name if api_cred else "binance"
    task = close_position_task.delay(current_user.id, request.symbol, exchange_name)
    add_user_log(current_user, db, "INFO", f"Close position enqueued: task_id={task.id}")
    return {"success": True, "message": f"Close position enqueued (task_id: {task.id})", "task_id": task.id}

@app.get("/system-status", response_model=schemas.SystemStatus)
async def system_status(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    api_cred = get_user_api_credential(current_user, db)
    settings = get_user_settings(current_user, db)
    connected = False
    connection_message = "Not configured"
    if api_cred and api_cred.encrypted_api_key and api_cred.encrypted_api_secret:
        connected, connection_message = test_exchange_connection(current_user, db)
    position = db.query(models.Position).filter(models.Position.user_id == current_user.id, models.Position.is_open == True).first()
    current_pnl = 0
    current_position_dict = None
    if position:
        try:
            exchange = get_exchange(current_user, db)
            ticker = exchange.fetch_ticker(position.symbol)
            current_price = ticker['last']
            if position.side == "LONG":
                current_pnl = (current_price - position.entry_price) * position.size
            else:
                current_pnl = (position.entry_price - current_price) * position.size
            current_position_dict = {"symbol": position.symbol, "side": position.side, "entry_price": position.entry_price, "size": position.size, "timestamp": position.timestamp.isoformat()}
        except:
            pass
    last_webhook_event = db.query(models.WebhookEvent).filter(models.WebhookEvent.user_id == current_user.id).order_by(models.WebhookEvent.timestamp.desc()).first()
    last_webhook = None
    if last_webhook_event:
        last_webhook = {"timestamp": last_webhook_event.timestamp.isoformat(), "action": last_webhook_event.action, "symbol": last_webhook_event.symbol, "price": last_webhook_event.price}
    last_trade = db.query(models.Trade).filter(models.Trade.user_id == current_user.id).order_by(models.Trade.timestamp.desc()).first()
    last_order = None
    if last_trade:
        last_order = {"id": last_trade.id, "timestamp": last_trade.timestamp.isoformat(), "action": last_trade.action, "symbol": last_trade.symbol, "price": last_trade.price, "size": last_trade.size, "exchange": last_trade.exchange, "result": last_trade.result}
    total_trades = db.query(models.Trade).filter(models.Trade.user_id == current_user.id).count()
    webhook_url = f"/webhook/{current_user.webhook_token}"
    return schemas.SystemStatus(api_configured=bool(api_cred and api_cred.encrypted_api_key and api_cred.encrypted_api_secret), exchange=api_cred.exchange_name if api_cred else "binance", connected=connected, connection_message=connection_message, auto_trading_enabled=settings.auto_trading_enabled, webhook_url=webhook_url, last_webhook=last_webhook, last_order=last_order, current_position=current_position_dict, current_pnl=current_pnl, total_pnl=settings.total_pnl, total_trades=total_trades, settings={"trading_mode": settings.trading_mode, "slippage": settings.slippage, "stop_loss_percent": settings.stop_loss_percent, "take_profit_percent": settings.take_profit_percent, "default_position_size": settings.default_position_size})

@app.get("/logs")
async def get_logs(limit: int = 100, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = db.query(models.Log).filter(models.Log.user_id == current_user.id).order_by(models.Log.timestamp.desc()).limit(limit).all()
    return {"logs": [schemas.LogOut.from_orm(log) for log in reversed(logs)], "total": db.query(models.Log).filter(models.Log.user_id == current_user.id).count()}

@app.get("/trades")
async def get_trades(symbol: Optional[str] = None, limit: int = 100, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(models.Trade).filter(models.Trade.user_id == current_user.id)
    if symbol:
        query = query.filter(models.Trade.symbol == symbol)
    trades = query.order_by(models.Trade.timestamp.desc()).limit(limit).all()
    total = query.count()
    return {"trades": [schemas.TradeOut.from_orm(trade) for trade in reversed(trades)], "total": total}

@app.post("/settings")
async def update_settings(request: schemas.SettingsRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        settings = get_user_settings(current_user, db)
        api_cred = get_user_api_credential(current_user, db)
        if request.exchange is not None and api_cred:
            api_cred.exchange_name = request.exchange
        if request.trading_mode is not None:
            settings.trading_mode = request.trading_mode
        if request.slippage is not None:
            settings.slippage = request.slippage
        if request.stop_loss_percent is not None:
            settings.stop_loss_percent = request.stop_loss_percent
        if request.take_profit_percent is not None:
            settings.take_profit_percent = request.take_profit_percent
        if request.default_position_size is not None:
            settings.default_position_size = request.default_position_size
        if request.auto_trading_enabled is not None:
            settings.auto_trading_enabled = request.auto_trading_enabled
            add_user_log(current_user, db, "INFO", f"Auto-trading {'enabled' if request.auto_trading_enabled else 'disabled'}")
        # Phase 2 settings
        if request.paper_trading_enabled is not None:
            settings.paper_trading_enabled = request.paper_trading_enabled
            add_user_log(current_user, db, "INFO", f"Paper trading {'enabled' if request.paper_trading_enabled else 'disabled'}")
        if request.trailing_stop_enabled is not None:
            settings.trailing_stop_enabled = request.trailing_stop_enabled
        if request.trailing_stop_percent is not None:
            settings.trailing_stop_percent = request.trailing_stop_percent
        if request.enable_notifications is not None:
            settings.enable_notifications = request.enable_notifications
        if request.notification_email is not None:
            settings.notification_email = request.notification_email
        if request.tiered_tp_enabled is not None:
            settings.tiered_tp_enabled = request.tiered_tp_enabled
        if request.tiered_tp_levels is not None:
            settings.tiered_tp_levels = request.tiered_tp_levels
        db.commit()
        add_user_log(current_user, db, "INFO", "Settings updated")
        # Create settings response with exchange from APICredential
        settings_dict = {
            "exchange": api_cred.exchange_name if api_cred else "binance",
            "trading_mode": settings.trading_mode,
            "slippage": settings.slippage,
            "stop_loss_percent": settings.stop_loss_percent,
            "take_profit_percent": settings.take_profit_percent,
            "default_position_size": settings.default_position_size,
            "auto_trading_enabled": settings.auto_trading_enabled,
            "total_pnl": settings.total_pnl,
            "paper_trading_enabled": settings.paper_trading_enabled,
            "trailing_stop_enabled": settings.trailing_stop_enabled,
            "trailing_stop_percent": settings.trailing_stop_percent,
            "enable_notifications": settings.enable_notifications,
            "notification_email": settings.notification_email,
            "tiered_tp_enabled": settings.tiered_tp_enabled,
            "tiered_tp_levels": settings.tiered_tp_levels
        }
        return {"success": True, "message": "Settings updated", "settings": schemas.SettingsOut(**settings_dict)}
    except Exception as e:
        add_user_log(current_user, db, "ERROR", f"Failed to update settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diagnostics", response_model=schemas.DiagnosticsOut)
async def run_diagnostics(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    api_cred = get_user_api_credential(current_user, db)
    diagnostics = schemas.DiagnosticsOut(timestamp=datetime.utcnow().isoformat(), api_configured=bool(api_cred and api_cred.encrypted_api_key and api_cred.encrypted_api_secret), exchange=api_cred.exchange_name if api_cred else "binance", tests=[])
    diagnostics.tests.append(schemas.DiagnosticTest(name="API Keys Configured", passed=bool(api_cred and api_cred.encrypted_api_key), message="API keys are configured" if api_cred and api_cred.encrypted_api_key else "API keys not configured"))
    if api_cred and api_cred.encrypted_api_key and api_cred.encrypted_api_secret:
        connected, message = test_exchange_connection(current_user, db)
        diagnostics.tests.append(schemas.DiagnosticTest(name="Exchange Connection", passed=connected, message=message))
    else:
        diagnostics.tests.append(schemas.DiagnosticTest(name="Exchange Connection", passed=False, message="Cannot test - API keys not configured"))
    settings = get_user_settings(current_user, db)
    diagnostics.tests.append(schemas.DiagnosticTest(name="Auto-Trading Status", passed=True, message=f"Auto-trading is {'enabled' if settings.auto_trading_enabled else 'disabled'}"))
    trade_count = db.query(models.Trade).filter(models.Trade.user_id == current_user.id).count()
    log_count = db.query(models.Log).filter(models.Log.user_id == current_user.id).count()
    diagnostics.tests.append(schemas.DiagnosticTest(name="Database Status", passed=True, message=f"Database active ({trade_count} trades, {log_count} logs)"))
    return diagnostics

@app.get("/system-health", response_model=schemas.SystemHealthOut)
async def get_system_health(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get system health metrics (Phase 2 feature)"""
    from datetime import timedelta
    
    # Calculate metrics
    active_users_count = db.query(models.User).count()
    
    # Count trades in last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    total_trades_24h = db.query(models.Trade).filter(
        models.Trade.timestamp >= twenty_four_hours_ago
    ).count()
    
    # For now, celery queue depth and failed tasks would require Redis inspection
    # We'll set placeholder values for now
    celery_queue_depth = 0
    failed_tasks_count = 0
    
    # Calculate uptime (simplified - time since first user registration)
    first_user = db.query(models.User).order_by(models.User.created_at).first()
    uptime_seconds = 0
    if first_user:
        uptime_seconds = int((datetime.utcnow() - first_user.created_at).total_seconds())
    
    health = models.SystemHealth(
        timestamp=datetime.utcnow(),
        celery_queue_depth=celery_queue_depth,
        failed_tasks_count=failed_tasks_count,
        active_users_count=active_users_count,
        total_trades_24h=total_trades_24h,
        uptime_seconds=uptime_seconds
    )
    
    return schemas.SystemHealthOut.from_orm(health)

@app.get("/settings", response_model=schemas.SettingsOut)
async def get_settings(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user settings"""
    settings = get_user_settings(current_user, db)
    api_cred = get_user_api_credential(current_user, db)
    # Create a temporary settings object with exchange name for response
    settings_dict = {
        "exchange": api_cred.exchange_name if api_cred else "binance",
        "trading_mode": settings.trading_mode,
        "slippage": settings.slippage,
        "stop_loss_percent": settings.stop_loss_percent,
        "take_profit_percent": settings.take_profit_percent,
        "default_position_size": settings.default_position_size,
        "auto_trading_enabled": settings.auto_trading_enabled,
        "total_pnl": settings.total_pnl,
        "paper_trading_enabled": settings.paper_trading_enabled,
        "trailing_stop_enabled": settings.trailing_stop_enabled,
        "trailing_stop_percent": settings.trailing_stop_percent,
        "enable_notifications": settings.enable_notifications,
        "notification_email": settings.notification_email,
        "tiered_tp_enabled": settings.tiered_tp_enabled,
        "tiered_tp_levels": settings.tiered_tp_levels
    }
    return schemas.SettingsOut(**settings_dict)

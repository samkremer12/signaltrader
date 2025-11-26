from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import ccxt
import logging
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# In-memory database
class InMemoryDB:
    def __init__(self):
        self.api_key: Optional[str] = None
        self.api_secret: Optional[str] = None
        self.exchange_name: str = "binance"
        self.webhook_url: str = ""
        self.auto_trading_enabled: bool = False
        self.trades: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []
        self.current_position: Optional[Dict[str, Any]] = None
        self.last_webhook: Optional[Dict[str, Any]] = None
        self.last_order: Optional[Dict[str, Any]] = None
        self.total_pnl: float = 0.0
        self.current_pnl: float = 0.0
        
        # Settings
        self.trading_mode: str = "market"  # market, limit, market_limit_fallback
        self.slippage: float = 0.5
        self.stop_loss_percent: float = 2.0
        self.take_profit_percent: float = 5.0
        self.default_position_size: float = 100.0  # USDT
        
    def add_log(self, level: str, message: str, data: Optional[Dict] = None):
        log_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        }
        self.logs.append(log_entry)
        logger.info(f"[{level}] {message}")
        
    def add_trade(self, action: str, symbol: str, price: float, size: float, 
                  exchange: str, result: str, order_id: Optional[str] = None):
        trade = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "symbol": symbol,
            "price": price,
            "size": size,
            "exchange": exchange,
            "result": result,
            "order_id": order_id
        }
        self.trades.append(trade)
        self.last_order = trade
        return trade

db = InMemoryDB()

# Pydantic models
class APIKeyRequest(BaseModel):
    api_key: str
    api_secret: str
    exchange: Optional[str] = "binance"

class WebhookRequest(BaseModel):
    action: str  # buy, sell, close
    symbol: str
    price: Optional[str] = None
    size: Optional[float] = None

class OrderRequest(BaseModel):
    symbol: str
    side: str  # buy or sell
    amount: float
    price: Optional[float] = None
    order_type: Optional[str] = "market"

class CloseOrderRequest(BaseModel):
    symbol: str

class SettingsRequest(BaseModel):
    exchange: Optional[str] = None
    trading_mode: Optional[str] = None
    slippage: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    default_position_size: Optional[float] = None
    auto_trading_enabled: Optional[bool] = None

# Exchange management
def get_exchange():
    """Get configured exchange instance"""
    if not db.api_key or not db.api_secret:
        raise HTTPException(status_code=400, detail="API keys not configured")
    
    try:
        exchange_class = getattr(ccxt, db.exchange_name)
        exchange = exchange_class({
            'apiKey': db.api_key,
            'secret': db.api_secret,
            'enableRateLimit': True,
        })
        return exchange
    except Exception as e:
        db.add_log("ERROR", f"Failed to initialize exchange: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize exchange: {str(e)}")

def test_exchange_connection():
    """Test if exchange connection is working"""
    try:
        exchange = get_exchange()
        balance = exchange.fetch_balance()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

# Endpoints
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/set-api-key")
async def set_api_key(request: APIKeyRequest):
    """Set API key and secret for exchange"""
    try:
        db.api_key = request.api_key
        db.api_secret = request.api_secret
        db.exchange_name = request.exchange or "binance"
        
        # Test connection
        connected, message = test_exchange_connection()
        
        if connected:
            db.add_log("INFO", f"API keys configured successfully for {db.exchange_name}")
            return {
                "success": True,
                "message": "API keys configured successfully",
                "exchange": db.exchange_name,
                "connected": True
            }
        else:
            db.add_log("WARNING", f"API keys set but connection test failed: {message}")
            return {
                "success": True,
                "message": "API keys set but connection test failed",
                "exchange": db.exchange_name,
                "connected": False,
                "error": message
            }
    except Exception as e:
        db.add_log("ERROR", f"Failed to set API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-webhook")
async def set_webhook(webhook_url: str):
    """Set webhook URL (for reference only)"""
    db.webhook_url = webhook_url
    db.add_log("INFO", f"Webhook URL set: {webhook_url}")
    return {"success": True, "webhook_url": webhook_url}

@app.get("/webhook-url")
async def get_webhook_url():
    """Get the webhook URL that should be used in TradingView"""
    # This will be the deployed backend URL + /webhook
    return {
        "webhook_url": db.webhook_url or "/webhook",
        "instructions": "Use this URL in TradingView alerts"
    }

@app.post("/webhook")
async def webhook(request: WebhookRequest):
    """Receive webhook from TradingView"""
    try:
        db.last_webhook = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": request.action,
            "symbol": request.symbol,
            "price": request.price
        }
        
        db.add_log("INFO", f"Webhook received: {request.action} {request.symbol} @ {request.price}")
        
        if not db.auto_trading_enabled:
            db.add_log("WARNING", "Auto-trading is disabled, ignoring webhook")
            return {
                "success": True,
                "message": "Webhook received but auto-trading is disabled",
                "action": request.action
            }
        
        # Process the webhook
        if request.action.lower() == "buy":
            result = await execute_buy(request.symbol, request.size)
        elif request.action.lower() == "sell":
            result = await execute_sell(request.symbol, request.size)
        elif request.action.lower() == "close":
            result = await close_position(request.symbol)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        return result
        
    except Exception as e:
        db.add_log("ERROR", f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_buy(symbol: str, size: Optional[float] = None):
    """Execute a buy order"""
    try:
        exchange = get_exchange()
        
        # Get current price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Calculate amount
        if size is None:
            size = db.default_position_size / current_price
        
        # Execute order based on trading mode
        if db.trading_mode == "market":
            order = exchange.create_market_buy_order(symbol, size)
        elif db.trading_mode == "limit":
            limit_price = current_price * (1 - db.slippage / 100)
            order = exchange.create_limit_buy_order(symbol, size, limit_price)
        else:  # market_limit_fallback
            try:
                order = exchange.create_market_buy_order(symbol, size)
            except:
                limit_price = current_price * (1 - db.slippage / 100)
                order = exchange.create_limit_buy_order(symbol, size, limit_price)
        
        # Record trade
        trade = db.add_trade(
            action="BUY",
            symbol=symbol,
            price=order.get('price', current_price),
            size=size,
            exchange=db.exchange_name,
            result="SUCCESS",
            order_id=order.get('id')
        )
        
        # Update position
        db.current_position = {
            "symbol": symbol,
            "side": "LONG",
            "entry_price": order.get('price', current_price),
            "size": size,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        db.add_log("INFO", f"Buy order executed: {symbol} @ {order.get('price', current_price)}")
        
        return {
            "success": True,
            "message": "Buy order executed",
            "order": order,
            "trade": trade
        }
        
    except Exception as e:
        db.add_log("ERROR", f"Buy order failed: {str(e)}")
        db.add_trade(
            action="BUY",
            symbol=symbol,
            price=0,
            size=size or 0,
            exchange=db.exchange_name,
            result=f"FAILED: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))

async def execute_sell(symbol: str, size: Optional[float] = None):
    """Execute a sell order"""
    try:
        exchange = get_exchange()
        
        # Get current price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Use position size if not specified
        if size is None and db.current_position and db.current_position['symbol'] == symbol:
            size = db.current_position['size']
        elif size is None:
            size = db.default_position_size / current_price
        
        # Execute order based on trading mode
        if db.trading_mode == "market":
            order = exchange.create_market_sell_order(symbol, size)
        elif db.trading_mode == "limit":
            limit_price = current_price * (1 + db.slippage / 100)
            order = exchange.create_limit_sell_order(symbol, size, limit_price)
        else:  # market_limit_fallback
            try:
                order = exchange.create_market_sell_order(symbol, size)
            except:
                limit_price = current_price * (1 + db.slippage / 100)
                order = exchange.create_limit_sell_order(symbol, size, limit_price)
        
        # Calculate PnL if closing a position
        pnl = 0
        if db.current_position and db.current_position['symbol'] == symbol:
            entry_price = db.current_position['entry_price']
            exit_price = order.get('price', current_price)
            if db.current_position['side'] == "LONG":
                pnl = (exit_price - entry_price) * size
            else:
                pnl = (entry_price - exit_price) * size
            
            db.total_pnl += pnl
            db.current_pnl = 0
            db.current_position = None
        
        # Record trade
        trade = db.add_trade(
            action="SELL",
            symbol=symbol,
            price=order.get('price', current_price),
            size=size,
            exchange=db.exchange_name,
            result=f"SUCCESS (PnL: ${pnl:.2f})",
            order_id=order.get('id')
        )
        
        db.add_log("INFO", f"Sell order executed: {symbol} @ {order.get('price', current_price)} (PnL: ${pnl:.2f})")
        
        return {
            "success": True,
            "message": "Sell order executed",
            "order": order,
            "trade": trade,
            "pnl": pnl
        }
        
    except Exception as e:
        db.add_log("ERROR", f"Sell order failed: {str(e)}")
        db.add_trade(
            action="SELL",
            symbol=symbol,
            price=0,
            size=size or 0,
            exchange=db.exchange_name,
            result=f"FAILED: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))

async def close_position(symbol: str):
    """Close current position"""
    if not db.current_position or db.current_position['symbol'] != symbol:
        raise HTTPException(status_code=400, detail="No open position for this symbol")
    
    return await execute_sell(symbol, db.current_position['size'])

@app.post("/place-order")
async def place_order(request: OrderRequest):
    """Manually place an order"""
    try:
        if request.side.lower() == "buy":
            return await execute_buy(request.symbol, request.amount)
        elif request.side.lower() == "sell":
            return await execute_sell(request.symbol, request.amount)
        else:
            raise HTTPException(status_code=400, detail="Side must be 'buy' or 'sell'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/close-order")
async def close_order(request: CloseOrderRequest):
    """Close an open position"""
    return await close_position(request.symbol)

@app.get("/system-status")
async def system_status():
    """Get current system status"""
    connected = False
    connection_message = "Not configured"
    
    if db.api_key and db.api_secret:
        connected, connection_message = test_exchange_connection()
    
    # Calculate current PnL if position is open
    current_pnl = 0
    if db.current_position:
        try:
            exchange = get_exchange()
            ticker = exchange.fetch_ticker(db.current_position['symbol'])
            current_price = ticker['last']
            entry_price = db.current_position['entry_price']
            size = db.current_position['size']
            
            if db.current_position['side'] == "LONG":
                current_pnl = (current_price - entry_price) * size
            else:
                current_pnl = (entry_price - current_price) * size
            
            db.current_pnl = current_pnl
        except:
            pass
    
    return {
        "api_configured": bool(db.api_key and db.api_secret),
        "exchange": db.exchange_name,
        "connected": connected,
        "connection_message": connection_message,
        "auto_trading_enabled": db.auto_trading_enabled,
        "webhook_url": db.webhook_url,
        "last_webhook": db.last_webhook,
        "last_order": db.last_order,
        "current_position": db.current_position,
        "current_pnl": current_pnl,
        "total_pnl": db.total_pnl,
        "total_trades": len(db.trades),
        "settings": {
            "trading_mode": db.trading_mode,
            "slippage": db.slippage,
            "stop_loss_percent": db.stop_loss_percent,
            "take_profit_percent": db.take_profit_percent,
            "default_position_size": db.default_position_size
        }
    }

@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get system logs"""
    return {
        "logs": db.logs[-limit:],
        "total": len(db.logs)
    }

@app.get("/trades")
async def get_trades(symbol: Optional[str] = None, limit: int = 100):
    """Get trade history"""
    trades = db.trades
    
    if symbol:
        trades = [t for t in trades if t['symbol'] == symbol]
    
    return {
        "trades": trades[-limit:],
        "total": len(trades)
    }

@app.post("/settings")
async def update_settings(request: SettingsRequest):
    """Update system settings"""
    try:
        if request.exchange is not None:
            db.exchange_name = request.exchange
        if request.trading_mode is not None:
            db.trading_mode = request.trading_mode
        if request.slippage is not None:
            db.slippage = request.slippage
        if request.stop_loss_percent is not None:
            db.stop_loss_percent = request.stop_loss_percent
        if request.take_profit_percent is not None:
            db.take_profit_percent = request.take_profit_percent
        if request.default_position_size is not None:
            db.default_position_size = request.default_position_size
        if request.auto_trading_enabled is not None:
            db.auto_trading_enabled = request.auto_trading_enabled
            db.add_log("INFO", f"Auto-trading {'enabled' if request.auto_trading_enabled else 'disabled'}")
        
        db.add_log("INFO", "Settings updated")
        
        return {
            "success": True,
            "message": "Settings updated",
            "settings": {
                "exchange": db.exchange_name,
                "trading_mode": db.trading_mode,
                "slippage": db.slippage,
                "stop_loss_percent": db.stop_loss_percent,
                "take_profit_percent": db.take_profit_percent,
                "default_position_size": db.default_position_size,
                "auto_trading_enabled": db.auto_trading_enabled
            }
        }
    except Exception as e:
        db.add_log("ERROR", f"Failed to update settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diagnostics")
async def run_diagnostics():
    """Run system diagnostics"""
    diagnostics = {
        "timestamp": datetime.utcnow().isoformat(),
        "api_configured": bool(db.api_key and db.api_secret),
        "exchange": db.exchange_name,
        "tests": []
    }
    
    # Test 1: API keys configured
    diagnostics["tests"].append({
        "name": "API Keys Configured",
        "passed": bool(db.api_key and db.api_secret),
        "message": "API keys are configured" if db.api_key else "API keys not configured"
    })
    
    # Test 2: Exchange connection
    if db.api_key and db.api_secret:
        connected, message = test_exchange_connection()
        diagnostics["tests"].append({
            "name": "Exchange Connection",
            "passed": connected,
            "message": message
        })
    else:
        diagnostics["tests"].append({
            "name": "Exchange Connection",
            "passed": False,
            "message": "Cannot test - API keys not configured"
        })
    
    # Test 3: Auto-trading status
    diagnostics["tests"].append({
        "name": "Auto-Trading Status",
        "passed": True,
        "message": f"Auto-trading is {'enabled' if db.auto_trading_enabled else 'disabled'}"
    })
    
    # Test 4: Database status
    diagnostics["tests"].append({
        "name": "Database Status",
        "passed": True,
        "message": f"In-memory database active ({len(db.trades)} trades, {len(db.logs)} logs)"
    })
    
    return diagnostics

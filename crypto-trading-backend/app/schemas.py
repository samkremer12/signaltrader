from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: str
    username: str
    is_admin: bool
    webhook_token: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

# API Key schemas
class APIKeyRequest(BaseModel):
    api_key: str
    api_secret: str
    exchange: Optional[str] = "binance"

class APIKeyResponse(BaseModel):
    success: bool
    message: str
    exchange: str
    connected: bool
    error: Optional[str] = None

# Webhook schemas
class WebhookRequest(BaseModel):
    action: str  # buy, sell, close
    symbol: str
    price: Optional[str] = None
    size: Optional[float] = None

class WebhookResponse(BaseModel):
    success: bool
    message: str
    action: str

# Trading schemas
class OrderRequest(BaseModel):
    symbol: str
    side: str  # buy or sell
    amount: float
    price: Optional[float] = None
    order_type: Optional[str] = "market"

class CloseOrderRequest(BaseModel):
    symbol: str

# Settings schemas
class SettingsRequest(BaseModel):
    exchange: Optional[str] = None
    trading_mode: Optional[str] = None
    slippage: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    default_position_size: Optional[float] = None
    auto_trading_enabled: Optional[bool] = None
    # Phase 2 fields
    paper_trading_enabled: Optional[bool] = None
    trailing_stop_enabled: Optional[bool] = None
    trailing_stop_percent: Optional[float] = None
    enable_notifications: Optional[bool] = None
    notification_email: Optional[str] = None
    tiered_tp_enabled: Optional[bool] = None
    tiered_tp_levels: Optional[str] = None

class SettingsOut(BaseModel):
    exchange: str
    trading_mode: str
    slippage: float
    stop_loss_percent: float
    take_profit_percent: float
    default_position_size: float
    auto_trading_enabled: bool
    total_pnl: float
    # Phase 2 fields
    paper_trading_enabled: bool
    trailing_stop_enabled: bool
    trailing_stop_percent: float
    enable_notifications: bool
    notification_email: Optional[str]
    tiered_tp_enabled: bool
    tiered_tp_levels: Optional[str]
    
    class Config:
        from_attributes = True

# Trade schemas
class TradeOut(BaseModel):
    id: str
    timestamp: datetime
    action: str
    symbol: str
    price: float
    size: float
    exchange: str
    result: str
    order_id: Optional[str] = None
    pnl: float
    # Phase 2 fields
    fees: float
    is_paper_trade: bool
    
    class Config:
        from_attributes = True

# Log schemas
class LogOut(BaseModel):
    id: str
    timestamp: datetime
    level: str
    message: str
    data: Optional[str] = None
    
    class Config:
        from_attributes = True

# Position schemas
class PositionOut(BaseModel):
    id: str
    symbol: str
    side: str
    entry_price: float
    size: float
    timestamp: datetime
    is_open: bool
    # Phase 2 fields
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    trailing_stop_price: Optional[float]
    initial_size: Optional[float]
    highest_price: Optional[float]
    
    class Config:
        from_attributes = True

# System status schemas
class SystemStatus(BaseModel):
    api_configured: bool
    exchange: str
    connected: bool
    connection_message: str
    auto_trading_enabled: bool
    webhook_url: str
    last_webhook: Optional[dict] = None
    last_order: Optional[dict] = None
    current_position: Optional[dict] = None
    current_pnl: float
    total_pnl: float
    total_trades: int
    settings: dict

# Diagnostics schemas
class DiagnosticTest(BaseModel):
    name: str
    passed: bool
    message: str

class DiagnosticsOut(BaseModel):
    timestamp: str
    api_configured: bool
    exchange: str
    tests: List[DiagnosticTest]

# System Health schemas (Phase 2)
class SystemHealthOut(BaseModel):
    timestamp: datetime
    celery_queue_depth: int
    failed_tasks_count: int
    active_users_count: int
    total_trades_24h: int
    uptime_seconds: int
    
    class Config:
        from_attributes = True

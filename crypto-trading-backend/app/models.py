from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    webhook_token = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    api_credentials = relationship("ApiCredential", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="user", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("Settings", back_populates="user", uselist=False, cascade="all, delete-orphan")

class ApiCredential(Base):
    __tablename__ = "api_credentials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    exchange_name = Column(String, nullable=False, default="binance")
    encrypted_api_key = Column(Text, nullable=True)
    encrypted_api_secret = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="api_credentials")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String, nullable=False)  # BUY, SELL, CLOSE
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    exchange = Column(String, nullable=False)
    result = Column(String, nullable=False)
    order_id = Column(String, nullable=True)
    pnl = Column(Float, default=0.0)
    
    # Phase 2 features
    fees = Column(Float, default=0.0)
    is_paper_trade = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="trades")

class Log(Base):
    __tablename__ = "logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON string
    
    user = relationship("User", back_populates="logs")

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # LONG, SHORT
    entry_price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_open = Column(Boolean, default=True)
    
    # Phase 2 features
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    trailing_stop_price = Column(Float, nullable=True)
    initial_size = Column(Float, nullable=True)  # Track original size for partial closes
    highest_price = Column(Float, nullable=True)  # Track highest price for trailing stops
    
    user = relationship("User", back_populates="positions")

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    auto_trading_enabled = Column(Boolean, default=False)
    trading_mode = Column(String, default="market")  # market, limit, market_limit_fallback
    slippage = Column(Float, default=0.5)
    stop_loss_percent = Column(Float, default=2.0)
    take_profit_percent = Column(Float, default=5.0)
    default_position_size = Column(Float, default=100.0)
    total_pnl = Column(Float, default=0.0)
    
    # Phase 2 features
    paper_trading_enabled = Column(Boolean, default=False)
    trailing_stop_enabled = Column(Boolean, default=False)
    trailing_stop_percent = Column(Float, default=1.0)
    enable_notifications = Column(Boolean, default=False)
    notification_email = Column(String, nullable=True)
    tiered_tp_enabled = Column(Boolean, default=False)
    tiered_tp_levels = Column(Text, nullable=True)  # JSON string: [{"percent": 3, "size_percent": 25}, ...]
    
    user = relationship("User", back_populates="settings")

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    price = Column(String, nullable=True)
    processed = Column(Boolean, default=False)
    
    user = relationship("User")

class SystemHealth(Base):
    __tablename__ = "system_health"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow)
    celery_queue_depth = Column(Integer, default=0)
    failed_tasks_count = Column(Integer, default=0)
    active_users_count = Column(Integer, default=0)
    total_trades_24h = Column(Integer, default=0)
    uptime_seconds = Column(Integer, default=0)

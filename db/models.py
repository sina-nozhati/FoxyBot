from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class PanelStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"

class Panel(Base):
    __tablename__ = 'panels'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    proxy_path = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    status = Column(Enum(PanelStatus), default=PanelStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    users = relationship("User", back_populates="panel")
    subscriptions = relationship("Subscription", back_populates="panel")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    wallet_balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    panel_id = Column(Integer, ForeignKey('panels.id'))
    panel = relationship("Panel", back_populates="users")
    subscriptions = relationship("Subscription", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

class Plan(Base):
    __tablename__ = 'plans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    duration_days = Column(Integer, nullable=False)
    traffic_gb = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    subscriptions = relationship("Subscription", back_populates="plan")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    traffic_used = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="subscriptions")
    panel_id = Column(Integer, ForeignKey('panels.id'))
    panel = relationship("Panel", back_populates="subscriptions")
    plan_id = Column(Integer, ForeignKey('plans.id'))
    plan = relationship("Plan", back_populates="subscriptions")

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    description = Column(String)
    receipt_image = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="transactions") 
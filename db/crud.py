from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
from . import models
from config import TRAFFIC_ALERT_THRESHOLD

# Panel CRUD
def create_panel(db: Session, name: str, domain: str, proxy_path: str, api_key: str) -> models.Panel:
    db_panel = models.Panel(
        name=name,
        domain=domain,
        proxy_path=proxy_path,
        api_key=api_key
    )
    db.add(db_panel)
    db.commit()
    db.refresh(db_panel)
    return db_panel

def get_panel(db: Session, panel_id: int) -> Optional[models.Panel]:
    return db.query(models.Panel).filter(models.Panel.id == panel_id).first()

def get_active_panels(db: Session) -> List[models.Panel]:
    return db.query(models.Panel).filter(models.Panel.status == models.PanelStatus.ACTIVE).all()

def update_panel_status(db: Session, panel_id: int, status: models.PanelStatus) -> Optional[models.Panel]:
    db_panel = get_panel(db, panel_id)
    if db_panel:
        db_panel.status = status
        db.commit()
        db.refresh(db_panel)
    return db_panel

# User CRUD
def create_user(db: Session, telegram_id: int, username: str, first_name: str, last_name: str) -> models.User:
    db_user = models.User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, telegram_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.telegram_id == telegram_id).first()

def update_user_wallet(db: Session, user_id: int, amount: float) -> Optional[models.User]:
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db_user.wallet_balance += amount
        db.commit()
        db.refresh(db_user)
    return db_user

# Plan CRUD
def create_plan(db: Session, name: str, description: str, duration_days: int, traffic_gb: float, price: float) -> models.Plan:
    db_plan = models.Plan(
        name=name,
        description=description,
        duration_days=duration_days,
        traffic_gb=traffic_gb,
        price=price
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

def get_active_plans(db: Session) -> List[models.Plan]:
    return db.query(models.Plan).filter(models.Plan.is_active == True).all()

# Subscription CRUD
def create_subscription(
    db: Session,
    user_id: int,
    panel_id: int,
    plan_id: int,
    uuid: str,
    start_date: datetime,
    end_date: datetime
) -> models.Subscription:
    db_subscription = models.Subscription(
        user_id=user_id,
        panel_id=panel_id,
        plan_id=plan_id,
        uuid=uuid,
        start_date=start_date,
        end_date=end_date
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

def get_user_subscriptions(db: Session, user_id: int) -> List[models.Subscription]:
    return db.query(models.Subscription).filter(models.Subscription.user_id == user_id).all()

def get_active_subscriptions(db: Session) -> List[models.Subscription]:
    return db.query(models.Subscription).filter(
        and_(
            models.Subscription.is_active == True,
            models.Subscription.end_date > datetime.utcnow()
        )
    ).all()

def update_subscription_traffic(db: Session, subscription_id: int, traffic_used: float) -> Optional[models.Subscription]:
    db_subscription = db.query(models.Subscription).filter(models.Subscription.id == subscription_id).first()
    if db_subscription:
        db_subscription.traffic_used = traffic_used
        db.commit()
        db.refresh(db_subscription)
    return db_subscription

def get_subscriptions_needing_traffic_alert(db: Session) -> List[models.Subscription]:
    return db.query(models.Subscription).filter(
        and_(
            models.Subscription.is_active == True,
            models.Subscription.end_date > datetime.utcnow(),
            models.Subscription.traffic_used / models.Subscription.plan.has(models.Plan.traffic_gb) >= TRAFFIC_ALERT_THRESHOLD
        )
    ).all()

def get_subscriptions_needing_expiry_alert(db: Session, days: int) -> List[models.Subscription]:
    alert_date = datetime.utcnow() + timedelta(days=days)
    return db.query(models.Subscription).filter(
        and_(
            models.Subscription.is_active == True,
            models.Subscription.end_date <= alert_date,
            models.Subscription.end_date > datetime.utcnow()
        )
    ).all()

# Transaction CRUD
def create_transaction(
    db: Session,
    user_id: int,
    amount: float,
    description: str,
    receipt_image: Optional[str] = None
) -> models.Transaction:
    db_transaction = models.Transaction(
        user_id=user_id,
        amount=amount,
        description=description,
        receipt_image=receipt_image
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_pending_transactions(db: Session) -> List[models.Transaction]:
    return db.query(models.Transaction).filter(
        models.Transaction.status == models.TransactionStatus.PENDING
    ).all()

def update_transaction_status(
    db: Session,
    transaction_id: int,
    status: models.TransactionStatus
) -> Optional[models.Transaction]:
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if db_transaction:
        db_transaction.status = status
        db.commit()
        db.refresh(db_transaction)
    return db_transaction 
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import models, crud
from config import PAYMENT_CARD_NUMBER

class PaymentManager:
    def __init__(self, db: Session, bot):
        self.db = db
        self.bot = bot

    def create_payment_request(
        self,
        user_id: int,
        amount: float,
        description: str,
        plan_name: str
    ) -> models.Transaction:
        """ایجاد درخواست پرداخت جدید"""
        transaction = crud.create_transaction(
            self.db,
            user_id=user_id,
            amount=amount,
            description=f"پرداخت {plan_name} - {description}"
        )
        
        # ایجاد دکمه‌های پرداخت
        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 پرداخت کردم",
                    callback_data=f"payment_confirm_{transaction.id}"
                ),
                InlineKeyboardButton(
                    "❌ انصراف",
                    callback_data=f"payment_cancel_{transaction.id}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال پیام پرداخت
        message = (
            f"💰 مبلغ {amount:,} تومان به شماره کارت زیر واریز کنید:\n"
            f"🏦 {PAYMENT_CARD_NUMBER}\n\n"
            f"📝 توضیحات: {description}\n"
            f"🆔 شناسه تراکنش: {transaction.id}\n\n"
            "⚠️ پس از پرداخت، تصویر رسید را ارسال کنید."
        )
        
        self.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )
        
        return transaction

    def handle_payment_receipt(
        self,
        user_id: int,
        transaction_id: int,
        receipt_image: str
    ) -> Optional[models.Transaction]:
        """پردازش تصویر رسید پرداخت"""
        transaction = self.db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id,
            models.Transaction.user_id == user_id,
            models.Transaction.status == models.TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            return None
            
        # بروزرسانی تراکنش با تصویر رسید
        transaction.receipt_image = receipt_image
        self.db.commit()
        
        # ارسال پیام به ادمین‌ها
        admin_message = (
            f"🔔 درخواست پرداخت جدید:\n"
            f"👤 کاربر: {user_id}\n"
            f"💰 مبلغ: {transaction.amount:,} تومان\n"
            f"📝 توضیحات: {transaction.description}\n"
            f"🆔 شناسه تراکنش: {transaction.id}"
        )
        
        # TODO: ارسال پیام به تمام ادمین‌ها
        # for admin_id in get_admin_ids():
        #     self.bot.send_message(
        #         chat_id=admin_id,
        #         text=admin_message,
        #         reply_markup=create_admin_payment_keyboard(transaction.id)
        #     )
        
        return transaction

    def confirm_payment(
        self,
        admin_id: int,
        transaction_id: int
    ) -> Optional[models.Transaction]:
        """تأیید پرداخت توسط ادمین"""
        transaction = self.db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id,
            models.Transaction.status == models.TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            return None
            
        # بروزرسانی وضعیت تراکنش
        transaction.status = models.TransactionStatus.COMPLETED
        self.db.commit()
        
        # بروزرسانی موجودی کیف پول کاربر
        crud.update_user_wallet(
            self.db,
            user_id=transaction.user_id,
            amount=transaction.amount
        )
        
        # ارسال پیام تأیید به کاربر
        user_message = (
            f"✅ پرداخت شما با موفقیت تأیید شد.\n"
            f"💰 مبلغ: {transaction.amount:,} تومان\n"
            f"📝 توضیحات: {transaction.description}"
        )
        
        self.bot.send_message(
            chat_id=transaction.user_id,
            text=user_message
        )
        
        return transaction

    def reject_payment(
        self,
        admin_id: int,
        transaction_id: int,
        reason: str
    ) -> Optional[models.Transaction]:
        """رد پرداخت توسط ادمین"""
        transaction = self.db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id,
            models.Transaction.status == models.TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            return None
            
        # بروزرسانی وضعیت تراکنش
        transaction.status = models.TransactionStatus.REJECTED
        transaction.description += f"\n❌ رد شده: {reason}"
        self.db.commit()
        
        # ارسال پیام رد به کاربر
        user_message = (
            f"❌ پرداخت شما رد شد.\n"
            f"💰 مبلغ: {transaction.amount:,} تومان\n"
            f"📝 دلیل: {reason}\n\n"
            "لطفاً با پشتیبانی تماس بگیرید."
        )
        
        self.bot.send_message(
            chat_id=transaction.user_id,
            text=user_message
        )
        
        return transaction

    def cancel_payment(
        self,
        user_id: int,
        transaction_id: int
    ) -> Optional[models.Transaction]:
        """لغو پرداخت توسط کاربر"""
        transaction = self.db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id,
            models.Transaction.user_id == user_id,
            models.Transaction.status == models.TransactionStatus.PENDING
        ).first()
        
        if not transaction:
            return None
            
        # بروزرسانی وضعیت تراکنش
        transaction.status = models.TransactionStatus.CANCELLED
        self.db.commit()
        
        # ارسال پیام لغو به کاربر
        user_message = (
            f"❌ پرداخت شما لغو شد.\n"
            f"💰 مبلغ: {transaction.amount:,} تومان\n"
            f"📝 توضیحات: {transaction.description}"
        )
        
        self.bot.send_message(
            chat_id=user_id,
            text=user_message
        )
        
        return transaction 
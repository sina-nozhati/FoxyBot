from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import models, crud
from config import PAYMENT_CARD_NUMBER

class PaymentManager:
    def __init__(self, db: Session, bot):
        """
        Initialize the PaymentManager.
        
        Args:
            db: Database session
            bot: Telegram bot instance
        """
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

    async def send_payment_request(self, chat_id: int, transaction: models.Transaction) -> None:
        """
        Send a payment request message to the user.
        
        Args:
            chat_id: Chat ID to send the message to
            transaction: Transaction object
        """
        # ایجاد دکمه‌های تایید و لغو
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ تأیید پرداخت",
                    callback_data=f"payment_confirm_{transaction.id}"
                ),
                InlineKeyboardButton(
                    "❌ لغو پرداخت",
                    callback_data=f"payment_cancel_{transaction.id}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال پیام به کاربر
        await self.bot.send_message(
            chat_id=chat_id,
            text=(
                f"💸 درخواست پرداخت:\n\n"
                f"💰 مبلغ: {transaction.amount:,} تومان\n"
                f"📝 توضیحات: {transaction.description}\n"
                f"📅 تاریخ: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                "لطفاً تصویر رسید پرداخت را ارسال کنید."
            ),
            reply_markup=reply_markup
        )
        
    async def handle_payment_receipt(self, user_id: int, chat_id: int, photo_id: str, transaction_id: Optional[int] = None) -> None:
        """
        Handle a payment receipt image.
        
        Args:
            user_id: User ID
            chat_id: Chat ID
            photo_id: Photo file ID
            transaction_id: Transaction ID (optional)
        """
        # اگر شناسه تراکنش ارسال نشده، آخرین تراکنش در انتظار کاربر را دریافت می‌کنیم
        if not transaction_id:
            transaction = self.db.query(models.Transaction)\
                .filter(models.Transaction.user_id == user_id, 
                        models.Transaction.status == models.TransactionStatus.PENDING)\
                .order_by(models.Transaction.created_at.desc())\
                .first()
                
            if not transaction:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="❌ هیچ تراکنش در انتظاری یافت نشد."
                )
                return
                
            transaction_id = transaction.id
            
        # بروزرسانی تراکنش با شناسه عکس
        transaction = self.db.query(models.Transaction).get(transaction_id)
        if not transaction:
            await self.bot.send_message(
                chat_id=chat_id,
                text="❌ تراکنش مورد نظر یافت نشد."
            )
            return
            
        transaction.receipt_photo_id = photo_id
        transaction.updated_at = datetime.utcnow()
        self.db.commit()
        
        # ارسال پیام تأیید به کاربر
        await self.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ رسید پرداخت با موفقیت دریافت شد.\n"
                "پس از تأیید مدیر، مبلغ به کیف پول شما اضافه خواهد شد."
            )
        )
        
        # ارسال اطلاعیه به ادمین‌ها
        admins = self.db.query(models.User).filter(models.User.is_admin == True).all()
        for admin in admins:
            # ایجاد دکمه‌های تأیید/رد برای ادمین
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ تأیید",
                        callback_data=f"admin_confirm_{transaction_id}"
                    ),
                    InlineKeyboardButton(
                        "❌ رد",
                        callback_data=f"admin_reject_{transaction_id}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # ارسال عکس و اطلاعات تراکنش به ادمین
            await self.bot.send_photo(
                chat_id=admin.telegram_id,
                photo=photo_id,
                caption=(
                    "💰 درخواست پرداخت جدید:\n\n"
                    f"👤 کاربر: {transaction.user.first_name} {transaction.user.last_name}\n"
                    f"🆔 شناسه کاربر: {transaction.user.telegram_id}\n"
                    f"💰 مبلغ: {transaction.amount:,} تومان\n"
                    f"📝 توضیحات: {transaction.description}\n"
                    f"📅 تاریخ: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}"
                ),
                reply_markup=reply_markup
            )
            
    async def confirm_payment(self, admin_id: int, transaction_id: int) -> None:
        """
        Confirm a payment transaction.
        
        Args:
            admin_id: Admin ID
            transaction_id: Transaction ID
        """
        # بررسی وجود تراکنش
        transaction = self.db.query(models.Transaction).get(transaction_id)
        if not transaction:
            await self.bot.send_message(
                chat_id=admin_id,
                text="❌ تراکنش مورد نظر یافت نشد."
            )
            return
            
        # بررسی وضعیت تراکنش
        if transaction.status != models.TransactionStatus.PENDING:
            await self.bot.send_message(
                chat_id=admin_id,
                text=f"❌ این تراکنش قبلاً {transaction.status.value} شده است."
            )
            return
            
        # تأیید تراکنش
        crud.update_transaction_status(
            self.db,
            transaction_id,
            models.TransactionStatus.COMPLETED
        )
        
        # اضافه کردن مبلغ به کیف پول کاربر
        crud.update_user_wallet(
            self.db,
            transaction.user_id,
            transaction.amount
        )
        
        # ارسال پیام تأیید به ادمین
        await self.bot.send_message(
            chat_id=admin_id,
            text=(
                "✅ تراکنش با موفقیت تأیید شد.\n"
                f"💰 مبلغ {transaction.amount:,} تومان به کیف پول کاربر اضافه شد."
            )
        )
        
        # ارسال پیام تأیید به کاربر
        await self.bot.send_message(
            chat_id=transaction.user.telegram_id,
            text=(
                "✅ پرداخت شما تأیید شد.\n"
                f"💰 مبلغ {transaction.amount:,} تومان به کیف پول شما اضافه شد.\n"
                f"💳 موجودی فعلی: {transaction.user.wallet_balance:,} تومان"
            )
        )
        
    async def reject_payment(self, admin_id: int, transaction_id: int, reason: str = "") -> None:
        """
        Reject a payment transaction.
        
        Args:
            admin_id: Admin ID
            transaction_id: Transaction ID
            reason: Rejection reason
        """
        # بررسی وجود تراکنش
        transaction = self.db.query(models.Transaction).get(transaction_id)
        if not transaction:
            await self.bot.send_message(
                chat_id=admin_id,
                text="❌ تراکنش مورد نظر یافت نشد."
            )
            return
            
        # بررسی وضعیت تراکنش
        if transaction.status != models.TransactionStatus.PENDING:
            await self.bot.send_message(
                chat_id=admin_id,
                text=f"❌ این تراکنش قبلاً {transaction.status.value} شده است."
            )
            return
            
        # رد تراکنش
        crud.update_transaction_status(
            self.db,
            transaction_id,
            models.TransactionStatus.REJECTED,
            description=f"{transaction.description} (دلیل رد: {reason})"
        )
        
        # ارسال پیام رد به ادمین
        await self.bot.send_message(
            chat_id=admin_id,
            text=(
                "✅ تراکنش با موفقیت رد شد."
            )
        )
        
        # ارسال پیام رد به کاربر
        reject_message = (
            "❌ پرداخت شما رد شد.\n"
            f"💰 مبلغ: {transaction.amount:,} تومان\n"
        )
        
        if reason:
            reject_message += f"📝 دلیل: {reason}\n"
            
        await self.bot.send_message(
            chat_id=transaction.user.telegram_id,
            text=reject_message
        )
        
    async def cancel_payment(self, user_id: int, transaction_id: int) -> None:
        """
        Cancel a payment transaction.
        
        Args:
            user_id: User ID
            transaction_id: Transaction ID
        """
        # بررسی وجود تراکنش
        transaction = self.db.query(models.Transaction).get(transaction_id)
        if not transaction:
            await self.bot.send_message(
                chat_id=user_id,
                text="❌ تراکنش مورد نظر یافت نشد."
            )
            return
            
        # بررسی مالکیت تراکنش
        if transaction.user_id != user_id:
            await self.bot.send_message(
                chat_id=user_id,
                text="❌ شما مجاز به لغو این تراکنش نیستید."
            )
            return
            
        # بررسی وضعیت تراکنش
        if transaction.status != models.TransactionStatus.PENDING:
            await self.bot.send_message(
                chat_id=user_id,
                text=f"❌ این تراکنش قبلاً {transaction.status.value} شده است."
            )
            return
            
        # لغو تراکنش
        crud.update_transaction_status(
            self.db,
            transaction_id,
            models.TransactionStatus.CANCELLED
        )
        
        # ارسال پیام لغو به کاربر
        await self.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ تراکنش با موفقیت لغو شد."
            )
        ) 
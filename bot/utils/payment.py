from typing import Dict, Optional
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_TELEGRAM_ID

from db import models, crud

logger = logging.getLogger(__name__)

class PaymentManager:
    """کلاس مدیریت پرداخت‌ها"""
    
    def __init__(self, db: Session, bot: Bot):
        """مقداردهی اولیه"""
        self.db = db
        self.bot = bot

    async def create_payment_request(self, user_id: int, amount: float, payment_type: str = "wallet_charge", description: str = "") -> models.Transaction:
        """ایجاد درخواست پرداخت جدید"""
        try:
            # ایجاد تراکنش جدید
            transaction = crud.create_transaction(
                self.db,
                user_id=user_id,
                amount=amount,
                description=description,
                payment_type=payment_type,
                status=models.TransactionStatus.PENDING
            )
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error creating payment request: {e}")
            return None
            
    async def send_payment_request(self, user_telegram_id: int, transaction):
        """ارسال پیام درخواست پرداخت به کاربر"""
        try:
            # پیام درخواست پرداخت با طراحی زیبا
            message = (
                f"💳 <b>درخواست پرداخت</b>\n\n"
                f"🆔 شناسه تراکنش: <code>{transaction.id}</code>\n"
                f"💰 مبلغ: <code>{transaction.amount:,}</code> تومان\n"
                f"📝 توضیحات: {transaction.description}\n"
                f"⏱ تاریخ: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"✅ لطفاً رسید پرداخت خود را ارسال کنید یا از دکمه‌های زیر استفاده کنید."
            )
            
            # ایجاد دکمه‌های تأیید/انصراف
            keyboard = [
                [
                    InlineKeyboardButton(
                        "📸 ارسال رسید",
                        callback_data=f"payment_confirm_{transaction.id}"
                    ),
                    InlineKeyboardButton(
                        "❌ انصراف",
                        callback_data=f"payment_cancel_{transaction.id}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # ارسال پیام به کاربر
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error sending payment request: {e}")
            
    async def handle_payment_receipt(self, user_id: int, chat_id: int, photo_id: str):
        """پردازش رسید پرداخت"""
        try:
            # یافتن آخرین تراکنش در انتظار کاربر
            transaction = self.db.query(models.Transaction).filter(
                models.Transaction.user_id == user_id,
                models.Transaction.status == models.TransactionStatus.PENDING
            ).order_by(models.Transaction.created_at.desc()).first()
            
            if not transaction:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="❌ هیچ تراکنش در انتظاری برای شما یافت نشد."
                )
                return
                
            # به‌روزرسانی تراکنش با شناسه عکس رسید
            transaction.receipt_photo_id = photo_id
            transaction.updated_at = datetime.now()
            self.db.commit()
            
            # ارسال پیام تأیید به کاربر
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ رسید پرداخت شما دریافت شد.\n\n"
                    "پس از بررسی توسط ادمین، نتیجه به شما اطلاع داده خواهد شد."
                )
            )
            
            # ارسال رسید به ادمین برای بررسی
            user = self.db.query(models.User).filter(models.User.id == transaction.user_id).first()
            
            admin_message = (
                f"🔔 <b>رسید پرداخت جدید</b>\n\n"
                f"👤 کاربر: {user.first_name} {user.last_name} (@{user.username})\n"
                f"🆔 شناسه تلگرام: <code>{user.telegram_id}</code>\n"
                f"💰 مبلغ: <code>{transaction.amount:,}</code> تومان\n"
                f"📝 توضیحات: {transaction.description}\n"
                f"⏱ تاریخ: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}"
            )
            
            # ایجاد دکمه‌های تأیید/رد برای ادمین
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ تأیید پرداخت",
                        callback_data=f"admin_confirm_{transaction.id}"
                    ),
                    InlineKeyboardButton(
                        "❌ رد پرداخت",
                        callback_data=f"admin_reject_{transaction.id}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # ارسال عکس به ادمین
            await self.bot.send_photo(
                chat_id=ADMIN_TELEGRAM_ID,
                photo=photo_id,
                caption=admin_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error handling receipt: {e}")
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ خطا در پردازش رسید: {str(e)}"
            )
            
    async def confirm_payment(self, admin_id: int, transaction_id: int):
        """تأیید پرداخت توسط ادمین"""
        try:
            # یافتن تراکنش
            transaction = self.db.query(models.Transaction).get(transaction_id)
            
            if not transaction:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text="❌ تراکنش یافت نشد."
                )
                return
                
            if transaction.status != models.TransactionStatus.PENDING:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=f"❌ وضعیت تراکنش قبلاً به {transaction.status.value} تغییر یافته است."
                )
                return
                
            # به‌روزرسانی وضعیت تراکنش
            transaction.status = models.TransactionStatus.COMPLETED
            transaction.updated_at = datetime.now()
            self.db.commit()
            
            # به‌روزرسانی موجودی کاربر
            user = self.db.query(models.User).get(transaction.user_id)
            crud.update_user_wallet(self.db, user.id, transaction.amount)
            
            # ارسال پیام تأیید به کاربر
            user_message = (
                f"✅ <b>پرداخت شما تأیید شد</b>\n\n"
                f"💰 مبلغ: <code>{transaction.amount:,}</code> تومان\n"
                f"💎 موجودی فعلی: <code>{user.wallet_balance:,}</code> تومان\n"
                f"📝 توضیحات: {transaction.description}\n\n"
                f"با تشکر از پرداخت شما! 🙏"
            )
            
            # ایجاد دکمه‌های پس از تأیید
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🛒 خرید اشتراک",
                        callback_data="view_plans"
                    ),
                    InlineKeyboardButton(
                        "👤 مشاهده پروفایل",
                        callback_data="view_profile"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=user_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            # ارسال پیام تأیید به ادمین
            admin_message = (
                f"✅ تراکنش با شناسه {transaction_id} با موفقیت تأیید شد.\n"
                f"👤 کاربر: {user.first_name} {user.last_name} (@{user.username})\n"
                f"💰 مبلغ: {transaction.amount:,} تومان"
            )
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=admin_message
            )
            
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            await self.bot.send_message(
                chat_id=admin_id,
                text=f"❌ خطا در تأیید پرداخت: {str(e)}"
            )
            
    async def reject_payment(self, admin_id: int, transaction_id: int, reason: str = ""):
        """رد پرداخت توسط ادمین"""
        try:
            # یافتن تراکنش
            transaction = self.db.query(models.Transaction).get(transaction_id)
            
            if not transaction:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text="❌ تراکنش یافت نشد."
                )
                return
                
            if transaction.status != models.TransactionStatus.PENDING:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=f"❌ وضعیت تراکنش قبلاً به {transaction.status.value} تغییر یافته است."
                )
                return
                
            # به‌روزرسانی وضعیت تراکنش
            transaction.status = models.TransactionStatus.REJECTED
            transaction.description += f" | دلیل رد: {reason}" if reason else " | رد شده توسط ادمین"
            transaction.updated_at = datetime.now()
            self.db.commit()
            
            # ارسال پیام رد به کاربر
            user = self.db.query(models.User).get(transaction.user_id)
            
            user_message = (
                f"❌ <b>پرداخت شما رد شد</b>\n\n"
                f"💰 مبلغ: <code>{transaction.amount:,}</code> تومان\n"
                f"📝 توضیحات: {transaction.description}\n\n"
                f"در صورت نیاز به اطلاعات بیشتر، با پشتیبانی تماس بگیرید."
            )
            
            # ایجاد دکمه‌های پس از رد
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 تلاش مجدد",
                        callback_data="wallet_charge"
                    ),
                    InlineKeyboardButton(
                        "💬 تماس با پشتیبانی",
                        callback_data="support"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=user_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            # ارسال پیام رد به ادمین
            admin_message = (
                f"❌ تراکنش با شناسه {transaction_id} رد شد.\n"
                f"👤 کاربر: {user.first_name} {user.last_name} (@{user.username})\n"
                f"💰 مبلغ: {transaction.amount:,} تومان\n"
                f"📝 دلیل: {reason}"
            )
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=admin_message
            )
            
        except Exception as e:
            logger.error(f"Error rejecting payment: {e}")
            await self.bot.send_message(
                chat_id=admin_id,
                text=f"❌ خطا در رد پرداخت: {str(e)}"
            )
            
    async def cancel_payment(self, user_id: int, transaction_id: int):
        """لغو پرداخت توسط کاربر"""
        try:
            # یافتن تراکنش
            transaction = self.db.query(models.Transaction).get(transaction_id)
            
            if not transaction:
                await self.bot.send_message(
                    chat_id=user_id,
                    text="❌ تراکنش یافت نشد."
                )
                return
                
            user = self.db.query(models.User).filter(models.User.telegram_id == user_id).first()
            
            if not user or user.id != transaction.user_id:
                await self.bot.send_message(
                    chat_id=user_id,
                    text="❌ شما مجاز به لغو این تراکنش نیستید."
                )
                return
                
            if transaction.status != models.TransactionStatus.PENDING:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ وضعیت تراکنش قبلاً به {transaction.status.value} تغییر یافته است."
                )
                return
                
            # به‌روزرسانی وضعیت تراکنش
            transaction.status = models.TransactionStatus.CANCELLED
            transaction.description += " | لغو شده توسط کاربر"
            transaction.updated_at = datetime.now()
            self.db.commit()
            
            # ارسال پیام لغو به کاربر
            user_message = (
                f"🚫 <b>تراکنش لغو شد</b>\n\n"
                f"💰 مبلغ: <code>{transaction.amount:,}</code> تومان\n"
                f"📝 توضیحات: {transaction.description}\n\n"
                f"تراکنش با موفقیت لغو شد."
            )
            
            # ایجاد دکمه‌های پس از لغو
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 درخواست مجدد",
                        callback_data="wallet_charge"
                    ),
                    InlineKeyboardButton(
                        "🔙 بازگشت به منو",
                        callback_data="back_to_main"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                chat_id=user_id,
                text=user_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            await self.bot.send_message(
                chat_id=user_id,
                text=f"❌ خطا در لغو پرداخت: {str(e)}"
            )
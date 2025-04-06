import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import USER_BOT_TOKEN, DATABASE_URL, DEFAULT_PLANS, PAYMENT_CARD_NUMBER
from db import models, crud
from bot.utils.hiddify import HiddifyAPI
from bot.utils.payment import PaymentManager

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات دیتابیس
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserBot:
    def __init__(self):
        self.application = Application.builder().token(USER_BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        # دستورات اصلی
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        
        # مدیریت اشتراک
        self.application.add_handler(CommandHandler("plans", self.list_plans_command))
        self.application.add_handler(CommandHandler("subscriptions", self.list_subscriptions_command))
        
        # مدیریت پرداخت
        self.application.add_handler(CommandHandler("wallet", self.wallet_command))
        
        # هندلرهای کالبک
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # هندلرهای پیام
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_receipt))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور شروع"""
        user = update.effective_user
        db = next(get_db())
        
        # بررسی وجود کاربر در دیتابیس
        db_user = crud.get_user(db, user.id)
        if not db_user:
            # ایجاد کاربر جدید
            db_user = crud.create_user(
                db,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
        
        welcome_message = (
            f"👋 سلام {user.first_name}!\n\n"
            "🔑 به ربات FoxyVPN خوش آمدید.\n\n"
            "📚 برای مشاهده دستورات موجود از /help استفاده کنید.\n"
            "💳 برای مشاهده پلن‌های موجود از /plans استفاده کنید."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنما"""
        help_message = (
            "📚 لیست دستورات:\n\n"
            "/plans - مشاهده پلن‌های موجود\n"
            "/subscriptions - مشاهده اشتراک‌های فعال\n"
            "/profile - مشاهده پروفایل\n"
            "/wallet - مشاهده موجودی و تراکنش‌ها\n"
            "/help - نمایش این راهنما"
        )
        await update.message.reply_text(help_message)

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش پروفایل"""
        db = next(get_db())
        user = crud.get_user(db, update.effective_user.id)
        
        if not user:
            await update.message.reply_text("❌ خطا در دریافت اطلاعات کاربر.")
            return
        
        subscriptions = crud.get_user_subscriptions(db, user.id)
        active_subscriptions = [s for s in subscriptions if s.is_active]
        
        message = (
            f"👤 پروفایل کاربری:\n\n"
            f"🆔 شناسه: {user.telegram_id}\n"
            f"👤 نام: {user.first_name} {user.last_name}\n"
            f"💰 موجودی: {user.wallet_balance:,} تومان\n"
            f"📦 تعداد اشتراک فعال: {len(active_subscriptions)}\n"
        )
        
        if active_subscriptions:
            message += "\n📊 اشتراک‌های فعال:\n"
            for sub in active_subscriptions:
                message += (
                    f"\n🔑 شناسه: {sub.id}\n"
                    f"📅 تاریخ انقضا: {sub.end_date.strftime('%Y-%m-%d')}\n"
                    f"📦 ترافیک مصرف شده: {sub.traffic_used:.2f} GB\n"
                )
        
        await update.message.reply_text(message)

    async def list_plans_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست پلن‌ها"""
        db = next(get_db())
        plans = crud.get_active_plans(db)
        
        if not plans:
            # ایجاد پلن‌های پیش‌فرض
            for plan_data in DEFAULT_PLANS:
                crud.create_plan(db, **plan_data)
            plans = crud.get_active_plans(db)
        
        message = "📊 لیست پلن‌های موجود:\n\n"
        for plan in plans:
            message += (
                f"📦 {plan.name}\n"
                f"📝 {plan.description}\n"
                f"⏱ مدت زمان: {plan.duration_days} روز\n"
                f"📊 ترافیک: {plan.traffic_gb} GB\n"
                f"💰 قیمت: {plan.price:,} تومان\n\n"
            )
        
        # ایجاد دکمه‌های خرید
        keyboard = []
        for plan in plans:
            keyboard.append([
                InlineKeyboardButton(
                    f"🛒 خرید {plan.name}",
                    callback_data=f"buy_plan_{plan.id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def list_subscriptions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست اشتراک‌ها"""
        db = next(get_db())
        subscriptions = crud.get_user_subscriptions(db, update.effective_user.id)
        
        if not subscriptions:
            await update.message.reply_text("❌ شما هیچ اشتراکی ندارید.")
            return
        
        message = "📊 لیست اشتراک‌های شما:\n\n"
        for sub in subscriptions:
            message += (
                f"🔑 شناسه: {sub.id}\n"
                f"📦 پلن: {sub.plan.name}\n"
                f"📅 تاریخ شروع: {sub.start_date.strftime('%Y-%m-%d')}\n"
                f"📅 تاریخ انقضا: {sub.end_date.strftime('%Y-%m-%d')}\n"
                f"📊 ترافیک مصرف شده: {sub.traffic_used:.2f} GB\n"
                f"📊 ترافیک کل: {sub.plan.traffic_gb} GB\n"
                f"✅ وضعیت: {'فعال' if sub.is_active else 'غیرفعال'}\n\n"
            )
        
        await update.message.reply_text(message)

    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش موجودی و تراکنش‌ها"""
        db = next(get_db())
        user = crud.get_user(db, update.effective_user.id)
        
        if not user:
            await update.message.reply_text("❌ خطا در دریافت اطلاعات کاربر.")
            return
        
        message = (
            f"💰 موجودی: {user.wallet_balance:,} تومان\n\n"
            "💳 برای افزایش موجودی، مبلغ مورد نظر را به شماره کارت زیر واریز کنید:\n"
            f"🔢 {PAYMENT_CARD_NUMBER}\n\n"
            "📸 پس از واریز، تصویر رسید را ارسال کنید."
        )
        
        # ایجاد دکمه‌های مدیریت تراکنش
        keyboard = [
            [
                InlineKeyboardButton(
                    "📊 تاریخچه تراکنش‌ها",
                    callback_data="transaction_history"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کالبک‌ها"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("buy_plan_"):
            plan_id = int(query.data.split("_")[2])
            db = next(get_db())
            
            # دریافت اطلاعات پلن و کاربر
            plan = db.query(models.Plan).get(plan_id)
            user = crud.get_user(db, query.from_user.id)
            
            if not plan or not user:
                await query.message.reply_text("❌ خطا در دریافت اطلاعات.")
                return
            
            # بررسی موجودی
            if user.wallet_balance < plan.price:
                await query.message.reply_text(
                    "❌ موجودی شما کافی نیست.\n"
                    "لطفاً ابتدا موجودی خود را افزایش دهید."
                )
                return
            
            # ایجاد تراکنش
            payment_manager = PaymentManager(db, self.application.bot)
            transaction = payment_manager.create_payment_request(
                user.id,
                plan.price,
                f"خرید پلن {plan.name}"
            )
            
            if transaction:
                context.user_data['current_transaction'] = transaction.id
                await query.message.reply_text(
                    "✅ درخواست پرداخت با موفقیت ثبت شد.\n"
                    "لطفاً تصویر رسید را ارسال کنید."
                )
            else:
                await query.message.reply_text(
                    "❌ خطا در ثبت درخواست پرداخت.\n"
                    "لطفاً دوباره تلاش کنید."
                )
        
        elif query.data == "transaction_history":
            db = next(get_db())
            transactions = db.query(models.Transaction).filter(
                models.Transaction.user_id == query.from_user.id
            ).order_by(models.Transaction.created_at.desc()).limit(10).all()
            
            if not transactions:
                await query.message.reply_text("❌ هیچ تراکنشی یافت نشد.")
                return
            
            message = "📊 آخرین تراکنش‌ها:\n\n"
            for transaction in transactions:
                message += (
                    f"🆔 شناسه: {transaction.id}\n"
                    f"💰 مبلغ: {transaction.amount:,} تومان\n"
                    f"📅 تاریخ: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"📝 وضعیت: {transaction.status.value}\n\n"
                )
            
            await query.message.reply_text(message)

    async def handle_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تصویر رسید پرداخت"""
        if not context.user_data.get('current_transaction'):
            await update.message.reply_text(
                "❌ لطفاً ابتدا یک تراکنش را انتخاب کنید."
            )
            return
        
        db = next(get_db())
        payment_manager = PaymentManager(db, self.application.bot)
        
        # دریافت فایل تصویر
        photo = update.message.photo[-1]
        file = await self.application.bot.get_file(photo.file_id)
        
        # ذخیره تصویر و بروزرسانی تراکنش
        transaction = payment_manager.handle_payment_receipt(
            update.effective_user.id,
            context.user_data['current_transaction'],
            file.file_path
        )
        
        if transaction:
            await update.message.reply_text(
                "✅ رسید پرداخت با موفقیت ثبت شد.\n"
                "لطفاً منتظر تأیید ادمین باشید."
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ثبت رسید پرداخت.\n"
                "لطفاً دوباره تلاش کنید."
            )

    def run(self):
        """اجرای ربات"""
        self.application.run_polling() 
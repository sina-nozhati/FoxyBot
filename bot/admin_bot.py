import logging
from typing import Dict, List, Optional
from datetime import datetime
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

from config import ADMIN_BOT_TOKEN, DATABASE_URL
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

class AdminBot:
    def __init__(self):
        self.application = Application.builder().token(ADMIN_BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        # دستورات اصلی
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # مدیریت پنل‌ها
        self.application.add_handler(CommandHandler("add_panel", self.add_panel_command))
        self.application.add_handler(CommandHandler("panels", self.list_panels_command))
        
        # مدیریت کاربران
        self.application.add_handler(CommandHandler("users", self.list_users_command))
        
        # مدیریت تراکنش‌ها
        self.application.add_handler(CommandHandler("transactions", self.list_transactions_command))
        
        # هندلرهای کالبک
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # هندلرهای پیام
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_receipt))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور شروع"""
        welcome_message = (
            "👋 به ربات مدیریت FoxyVPN خوش آمدید!\n\n"
            "🔑 این ربات برای مدیریت پنل‌ها، کاربران و تراکنش‌ها استفاده می‌شود.\n\n"
            "📚 برای مشاهده دستورات موجود از /help استفاده کنید."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنما"""
        help_message = (
            "📚 لیست دستورات:\n\n"
            "/add_panel - افزودن پنل جدید\n"
            "/panels - مشاهده لیست پنل‌ها\n"
            "/users - مشاهده لیست کاربران\n"
            "/transactions - مشاهده لیست تراکنش‌ها\n"
            "/help - نمایش این راهنما"
        )
        await update.message.reply_text(help_message)

    async def add_panel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور افزودن پنل"""
        if not context.args:
            await update.message.reply_text(
                "❌ لطفاً لینک پنل را وارد کنید.\n"
                "مثال: /add_panel https://domain.com/{proxy_path}/{api_key}/"
            )
            return

        panel_url = context.args[0]
        try:
            # استخراج اطلاعات پنل از URL
            parts = panel_url.split("/")
            domain = parts[2]
            proxy_path = parts[3]
            api_key = parts[4]

            # بررسی اعتبار پنل
            hiddify = HiddifyAPI(domain, proxy_path, api_key)
            if not hiddify.check_panel_status():
                await update.message.reply_text("❌ پنل نامعتبر است یا در دسترس نیست.")
                return

            # ذخیره پنل در دیتابیس
            db = next(get_db())
            panel = crud.create_panel(
                db,
                name=f"Panel {domain}",
                domain=domain,
                proxy_path=proxy_path,
                api_key=api_key
            )

            await update.message.reply_text(
                f"✅ پنل با موفقیت افزوده شد.\n"
                f"🔑 شناسه: {panel.id}\n"
                f"🌐 دامنه: {panel.domain}"
            )

        except Exception as e:
            logger.error(f"Error adding panel: {e}")
            await update.message.reply_text("❌ خطا در افزودن پنل. لطفاً دوباره تلاش کنید.")

    async def list_panels_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست پنل‌ها"""
        db = next(get_db())
        panels = crud.get_active_panels(db)

        if not panels:
            await update.message.reply_text("❌ هیچ پنل فعالی یافت نشد.")
            return

        message = "📊 لیست پنل‌های فعال:\n\n"
        for panel in panels:
            hiddify = HiddifyAPI(panel.domain, panel.proxy_path, panel.api_key)
            try:
                status = hiddify.get_server_status()
                message += (
                    f"🔑 شناسه: {panel.id}\n"
                    f"🌐 دامنه: {panel.domain}\n"
                    f"📡 وضعیت: {panel.status.value}\n"
                    f"💻 CPU: {status['stats']['cpu']}%\n"
                    f"💾 RAM: {status['stats']['ram']}%\n"
                    f"📦 دیسک: {status['stats']['disk']}%\n\n"
                )
            except:
                message += (
                    f"🔑 شناسه: {panel.id}\n"
                    f"🌐 دامنه: {panel.domain}\n"
                    f"❌ خطا در دریافت وضعیت\n\n"
                )

        await update.message.reply_text(message)

    async def list_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست کاربران"""
        db = next(get_db())
        users = db.query(models.User).all()

        if not users:
            await update.message.reply_text("❌ هیچ کاربری یافت نشد.")
            return

        message = "👥 لیست کاربران:\n\n"
        for user in users:
            subscriptions = crud.get_user_subscriptions(db, user.id)
            message += (
                f"👤 نام: {user.first_name} {user.last_name}\n"
                f"🆔 شناسه: {user.telegram_id}\n"
                f"💰 موجودی: {user.wallet_balance:,} تومان\n"
                f"📦 تعداد اشتراک: {len(subscriptions)}\n\n"
            )

        await update.message.reply_text(message)

    async def list_transactions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست تراکنش‌ها"""
        db = next(get_db())
        transactions = crud.get_pending_transactions(db)

        if not transactions:
            await update.message.reply_text("❌ هیچ تراکنش در انتظاری یافت نشد.")
            return

        message = "💰 لیست تراکنش‌های در انتظار:\n\n"
        for transaction in transactions:
            message += (
                f"🆔 شناسه: {transaction.id}\n"
                f"👤 کاربر: {transaction.user.telegram_id}\n"
                f"💰 مبلغ: {transaction.amount:,} تومان\n"
                f"📝 توضیحات: {transaction.description}\n\n"
            )

        await update.message.reply_text(message)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کالبک‌ها"""
        query = update.callback_query
        await query.answer()

        if query.data.startswith("payment_"):
            action, transaction_id = query.data.split("_")[1:]
            db = next(get_db())
            payment_manager = PaymentManager(db, self.application.bot)

            if action == "confirm":
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
                await query.message.reply_text(
                    "لطفاً تراکنش را تأیید یا رد کنید:",
                    reply_markup=reply_markup
                )

            elif action == "cancel":
                payment_manager.cancel_payment(query.from_user.id, int(transaction_id))

        elif query.data.startswith("admin_"):
            action, transaction_id = query.data.split("_")[1:]
            db = next(get_db())
            payment_manager = PaymentManager(db, self.application.bot)

            if action == "confirm":
                payment_manager.confirm_payment(query.from_user.id, int(transaction_id))
            elif action == "reject":
                # درخواست دلیل رد
                context.user_data['rejecting_transaction'] = int(transaction_id)
                await query.message.reply_text(
                    "لطفاً دلیل رد تراکنش را وارد کنید:"
                )

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
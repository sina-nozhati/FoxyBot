import logging
from typing import Dict, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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
        self.application.add_handler(CommandHandler("menu", self.admin_menu_command))
        
        # مدیریت پنل‌ها
        self.application.add_handler(CommandHandler("add_panel", self.add_panel_command))
        self.application.add_handler(CommandHandler("panels", self.list_panels_command))
        
        # مدیریت کاربران
        self.application.add_handler(CommandHandler("users", self.list_users_command))
        self.application.add_handler(CommandHandler("search_user", self.search_user_command))
        self.application.add_handler(CommandHandler("add_user", self.add_user_command))
        
        # مدیریت تراکنش‌ها
        self.application.add_handler(CommandHandler("transactions", self.list_transactions_command))
        
        # هندلرهای کالبک
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # هندلرهای پیام
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_receipt))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور شروع"""
        welcome_message = (
            "👋 به ربات مدیریت FoxyVPN خوش آمدید!\n\n"
            "🔑 این ربات برای مدیریت پنل‌ها، کاربران و تراکنش‌ها استفاده می‌شود.\n\n"
            "📚 برای مشاهده منوی اصلی، از دستور /menu استفاده کنید."
        )
        await self.admin_menu_command(update, context)
        await update.message.reply_text(welcome_message)

    async def admin_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی اصلی ادمین"""
        # منوی مدیریت کاربران
        user_management_keyboard = [
            [
                InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
                InlineKeyboardButton("➕ افزودن کاربر", callback_data="admin_add_user")
            ],
            [
                InlineKeyboardButton("🤖 مدیریت ربات کاربران", callback_data="admin_manage_user_bot")
            ],
            [
                InlineKeyboardButton("📊 وضعیت سرور", callback_data="admin_server_status"),
                InlineKeyboardButton("ℹ️", callback_data="admin_help"),
                InlineKeyboardButton("💾 بکاپ پنل", callback_data="admin_panel_backup")
            ],
            [
                InlineKeyboardButton("🔧 تنظیمات", callback_data="admin_settings"),
                InlineKeyboardButton("💲 تراکنش‌ها", callback_data="admin_transactions")
            ],
            [
                InlineKeyboardButton("📌 پنل‌ها", callback_data="admin_panels")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(user_management_keyboard)
        
        await update.message.reply_text(
            "👤 مدیریت کاربران",
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنما"""
        help_message = (
            "📚 لیست دستورات:\n\n"
            "/menu - منوی اصلی\n"
            "/add_panel - افزودن پنل جدید\n"
            "/panels - مشاهده لیست پنل‌ها\n"
            "/users - مشاهده لیست کاربران\n"
            "/search_user - جستجوی کاربر\n"
            "/add_user - افزودن کاربر جدید\n"
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
            if panel_url.endswith("/"):
                panel_url = panel_url[:-1]
                
            parts = panel_url.split("/")
            if len(parts) < 5:
                await update.message.reply_text("❌ فرمت URL نامعتبر است.")
                return
                
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

        for panel in panels:
            hiddify = HiddifyAPI(panel.domain, panel.proxy_path, panel.api_key)
            try:
                status = hiddify.get_server_status()
                message = (
                    f"🔷 <b>پنل {panel.id}: {panel.domain}</b>\n\n"
                    f"📡 وضعیت: <code>{panel.status.value}</code>\n"
                    f"💻 CPU: <code>{status['stats']['cpu']}%</code>\n"
                    f"💾 RAM: <code>{status['stats']['ram']}%</code>\n"
                    f"📦 دیسک: <code>{status['stats']['disk']}%</code>\n"
                )
                
                # ایجاد دکمه‌های مدیریت پنل
                keyboard = [
                    [
                        InlineKeyboardButton("👥 کاربران", callback_data=f"panel_users_{panel.id}"),
                        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"panel_refresh_{panel.id}")
                    ],
                    [
                        InlineKeyboardButton("⚙️ تنظیمات", callback_data=f"panel_settings_{panel.id}"),
                        InlineKeyboardButton("❌ حذف", callback_data=f"panel_delete_{panel.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                
            except Exception as e:
                message = (
                    f"🔷 <b>پنل {panel.id}: {panel.domain}</b>\n\n"
                    f"❌ خطا در دریافت وضعیت: {str(e)}"
                )
                
                # ایجاد دکمه‌های مدیریت پنل
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"panel_refresh_{panel.id}"),
                        InlineKeyboardButton("❌ حذف", callback_data=f"panel_delete_{panel.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

    async def search_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """جستجوی کاربر"""
        if not context.args:
            await update.message.reply_text(
                "❌ لطفاً شناسه کاربر یا نام کاربری را وارد کنید.\n"
                "مثال: /search_user 123456789 یا /search_user username"
            )
            return
            
        search_term = context.args[0]
        db = next(get_db())
        
        # جستجو بر اساس شناسه کاربر
        if search_term.isdigit():
            user = crud.get_user(db, int(search_term))
            if user:
                await self.display_user_info(update, user, db)
                return
                
        # جستجو بر اساس نام کاربری
        users = db.query(models.User).filter(
            models.User.username.ilike(f"%{search_term}%") | 
            models.User.first_name.ilike(f"%{search_term}%") | 
            models.User.last_name.ilike(f"%{search_term}%")
        ).all()
        
        if not users:
            await update.message.reply_text("❌ هیچ کاربری یافت نشد.")
            return
            
        if len(users) == 1:
            await self.display_user_info(update, users[0], db)
        else:
            # نمایش لیست کاربران یافت شده
            message = "👥 کاربران یافت شده:\n\n"
            keyboard = []
            
            for user in users:
                message += f"👤 {user.first_name} {user.last_name} - @{user.username} - ID: {user.telegram_id}\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{user.first_name} {user.last_name}",
                        callback_data=f"user_info_{user.id}"
                    )
                ])
                
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def add_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """افزودن کاربر جدید"""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ لطفاً شناسه تلگرام و نام کاربر را وارد کنید.\n"
                "مثال: /add_user 123456789 علی"
            )
            return
            
        telegram_id = context.args[0]
        first_name = context.args[1]
        last_name = context.args[2] if len(context.args) > 2 else ""
        
        if not telegram_id.isdigit():
            await update.message.reply_text("❌ شناسه تلگرام باید عددی باشد.")
            return
            
        db = next(get_db())
        
        # بررسی وجود کاربر
        user = crud.get_user(db, int(telegram_id))
        if user:
            await update.message.reply_text(
                f"❌ کاربری با این شناسه از قبل وجود دارد.\n"
                f"👤 {user.first_name} {user.last_name} - ID: {user.telegram_id}"
            )
            return
            
        # ایجاد کاربر جدید
        user = crud.create_user(
            db,
            telegram_id=int(telegram_id),
            username="",
            first_name=first_name,
            last_name=last_name
        )
        
        await update.message.reply_text(
            f"✅ کاربر با موفقیت افزوده شد.\n"
            f"👤 {user.first_name} {user.last_name} - ID: {user.telegram_id}"
        )

    async def display_user_info(self, update: Update, user: models.User, db: Session):
        """نمایش اطلاعات کاربر"""
        subscriptions = crud.get_user_subscriptions(db, user.id)
        active_subscriptions = [s for s in subscriptions if s.is_active]
        
        message = (
            f"👤 <b>{user.first_name} {user.last_name}</b>\n\n"
            f"🆔 شناسه تلگرام: <code>{user.telegram_id}</code>\n"
            f"👤 نام کاربری: @{user.username}\n"
            f"💰 موجودی: <code>{user.wallet_balance:,}</code> تومان\n"
            f"📦 تعداد اشتراک فعال: <code>{len(active_subscriptions)}</code>\n"
        )
        
        # ایجاد دکمه‌های مدیریت کاربر
        keyboard = [
            [
                InlineKeyboardButton("💰 افزایش موجودی", callback_data=f"user_add_balance_{user.id}"),
                InlineKeyboardButton("📦 اشتراک‌ها", callback_data=f"user_subscriptions_{user.id}")
            ],
            [
                InlineKeyboardButton("📊 گزارش تراکنش‌ها", callback_data=f"user_transactions_{user.id}"),
                InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"user_refresh_{user.id}")
            ],
            [
                InlineKeyboardButton("⚙️ تنظیمات", callback_data=f"user_settings_{user.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

    async def list_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست کاربران"""
        db = next(get_db())
        users = db.query(models.User).all()

        if not users:
            await update.message.reply_text("❌ هیچ کاربری یافت نشد.")
            return

        message = "👥 لیست کاربران:\n\n"
        keyboard = []
        
        for i, user in enumerate(users[:10]):  # نمایش 10 کاربر اول
            message += f"{i+1}. 👤 {user.first_name} {user.last_name} - ID: {user.telegram_id}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{user.first_name} {user.last_name}",
                    callback_data=f"user_info_{user.id}"
                )
            ])
            
        if len(users) > 10:
            keyboard.append([
                InlineKeyboardButton(
                    "صفحه بعد ⏩",
                    callback_data="users_page_2"
                )
            ])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def list_transactions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست تراکنش‌ها"""
        db = next(get_db())
        transactions = crud.get_pending_transactions(db)

        if not transactions:
            await update.message.reply_text("❌ هیچ تراکنش در انتظاری یافت نشد.")
            return

        for transaction in transactions:
            message = (
                f"💰 <b>تراکنش #{transaction.id}</b>\n\n"
                f"👤 کاربر: {transaction.user.first_name} {transaction.user.last_name}\n"
                f"🆔 شناسه کاربر: <code>{transaction.user.telegram_id}</code>\n"
                f"💰 مبلغ: <code>{transaction.amount:,}</code> تومان\n"
                f"📝 توضیحات: {transaction.description}\n"
                f"⏰ تاریخ: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
            
            # ایجاد دکمه‌های مدیریت تراکنش
            keyboard = [
                [
                    InlineKeyboardButton("✅ تأیید", callback_data=f"admin_confirm_{transaction.id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"admin_reject_{transaction.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کالبک‌ها"""
        query = update.callback_query
        await query.answer()
        
        # بررسی نوع کالبک
        data = query.data
        
        # کالبک‌های مربوط به منوی اصلی
        if data == "admin_search_user":
            await query.message.reply_text(
                "🔍 لطفاً شناسه کاربر یا نام کاربری را وارد کنید:\n"
                "مثال: 123456789 یا username"
            )
            context.user_data['waiting_for'] = 'search_user'
        
        elif data == "admin_add_user":
            await query.message.reply_text(
                "➕ لطفاً اطلاعات کاربر جدید را وارد کنید:\n"
                "مثال: 123456789 علی رضایی"
            )
            context.user_data['waiting_for'] = 'add_user'
            
        elif data == "admin_manage_user_bot":
            # منوی مدیریت ربات کاربران
            keyboard = [
                [
                    InlineKeyboardButton("📊 آمار کاربران", callback_data="user_bot_stats"),
                    InlineKeyboardButton("📝 پیام همگانی", callback_data="user_bot_broadcast")
                ],
                [
                    InlineKeyboardButton("⚙️ تنظیمات ربات", callback_data="user_bot_settings"),
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "🤖 مدیریت ربات کاربران",
                reply_markup=reply_markup
            )
            
        elif data == "admin_server_status":
            # نمایش وضعیت سرورها
            db = next(get_db())
            panels = crud.get_active_panels(db)
            
            if not panels:
                await query.message.reply_text("❌ هیچ پنل فعالی یافت نشد.")
                return
                
            message = "📊 <b>وضعیت سرورها</b>\n\n"
            
            for panel in panels:
                hiddify = HiddifyAPI(panel.domain, panel.proxy_path, panel.api_key)
                try:
                    status = hiddify.get_server_status()
                    message += (
                        f"🔷 <b>{panel.domain}</b>\n"
                        f"💻 CPU: <code>{status['stats']['cpu']}%</code>\n"
                        f"💾 RAM: <code>{status['stats']['ram']}%</code>\n"
                        f"📦 دیسک: <code>{status['stats']['disk']}%</code>\n\n"
                    )
                except:
                    message += (
                        f"🔷 <b>{panel.domain}</b>\n"
                        f"❌ خطا در دریافت وضعیت\n\n"
                    )
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_server_status"),
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
        elif data == "admin_panel_backup":
            # منوی بکاپ‌گیری از پنل‌ها
            db = next(get_db())
            panels = crud.get_active_panels(db)
            
            if not panels:
                await query.message.reply_text("❌ هیچ پنل فعالی یافت نشد.")
                return
                
            keyboard = []
            for panel in panels:
                keyboard.append([
                    InlineKeyboardButton(
                        f"💾 بکاپ از {panel.domain}",
                        callback_data=f"backup_panel_{panel.id}"
                    )
                ])
                
            keyboard.append([
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main_menu")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "💾 <b>بکاپ‌گیری از پنل‌ها</b>\n\n"
                "لطفاً پنل مورد نظر را انتخاب کنید:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        elif data == "admin_help":
            # راهنمای ربات
            help_message = (
                "📚 <b>راهنمای ربات مدیریت</b>\n\n"
                "🔹 <b>مدیریت کاربران:</b>\n"
                "- جستجو، افزودن و مدیریت کاربران\n\n"
                "🔹 <b>مدیریت ربات کاربران:</b>\n"
                "- ارسال پیام همگانی و مشاهده آمار\n\n"
                "🔹 <b>وضعیت سرور:</b>\n"
                "- مشاهده آمار سرورها\n\n"
                "🔹 <b>بکاپ پنل:</b>\n"
                "- تهیه نسخه پشتیبان از پنل‌ها\n\n"
                "🔹 <b>تنظیمات:</b>\n"
                "- پیکربندی ربات و پنل‌ها\n\n"
                "🔹 <b>تراکنش‌ها:</b>\n"
                "- مدیریت پرداخت‌ها و تراکنش‌ها\n\n"
                "🔹 <b>پنل‌ها:</b>\n"
                "- مدیریت پنل‌های هیدیفای\n\n"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                help_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        elif data == "admin_settings":
            # منوی تنظیمات
            keyboard = [
                [
                    InlineKeyboardButton("⚙️ تنظیمات عمومی", callback_data="general_settings"),
                    InlineKeyboardButton("💰 تنظیمات پرداخت", callback_data="payment_settings")
                ],
                [
                    InlineKeyboardButton("👥 تنظیمات کاربران", callback_data="user_settings"),
                    InlineKeyboardButton("📊 تنظیمات ترافیک", callback_data="traffic_settings")
                ],
                [
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "⚙️ <b>تنظیمات</b>\n\n"
                "لطفاً بخش مورد نظر را انتخاب کنید:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        elif data == "admin_transactions":
            # لیست تراکنش‌ها
            await self.list_transactions_command(update, context)
            
        elif data == "admin_panels":
            # لیست پنل‌ها
            await self.list_panels_command(update, context)
            
        elif data == "back_to_main_menu":
            # بازگشت به منوی اصلی
            await self.admin_menu_command(update, context)
        
        # کالبک‌های مربوط به پرداخت
        elif data.startswith("payment_"):
            action, transaction_id = data.split("_")[1:]
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
                await payment_manager.cancel_payment(query.from_user.id, int(transaction_id))

        elif data.startswith("admin_"):
            action, transaction_id = data.split("_")[1:]
            db = next(get_db())
            payment_manager = PaymentManager(db, self.application.bot)

            if action == "confirm":
                await payment_manager.confirm_payment(query.from_user.id, int(transaction_id))
            elif action == "reject":
                # درخواست دلیل رد
                context.user_data['rejecting_transaction'] = int(transaction_id)
                await query.message.reply_text(
                    "لطفاً دلیل رد تراکنش را وارد کنید:"
                )

    async def handle_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش رسید پرداخت"""
        user_id = update.effective_user.id
        photo = update.message.photo[-1]  # بزرگترین سایز عکس
        
        db = next(get_db())
        payment_manager = PaymentManager(db, self.application.bot)
        
        # اگر در حال رد تراکنش هستیم، تصویر را نادیده می‌گیریم
        if 'rejecting_transaction' in context.user_data:
            await update.message.reply_text("❌ لطفاً ابتدا دلیل رد تراکنش را وارد کنید.")
            return
        
        # پردازش رسید پرداخت
        await payment_manager.handle_payment_receipt(
            user_id=user_id,
            chat_id=update.effective_chat.id,
            photo_id=photo.file_id
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام‌های متنی"""
        text = update.message.text
        
        # اگر کاربر در حال انجام عملیاتی است
        if 'waiting_for' in context.user_data:
            action = context.user_data['waiting_for']
            
            if action == 'search_user':
                # جستجوی کاربر
                context.args = [text]
                await self.search_user_command(update, context)
                del context.user_data['waiting_for']
                
            elif action == 'add_user':
                # افزودن کاربر
                parts = text.split()
                if len(parts) < 2:
                    await update.message.reply_text(
                        "❌ لطفاً شناسه تلگرام و نام کاربر را وارد کنید.\n"
                        "مثال: 123456789 علی رضایی"
                    )
                    return
                context.args = parts
                await self.add_user_command(update, context)
                del context.user_data['waiting_for']
                
            elif action == 'reject_reason':
                # دلیل رد تراکنش
                transaction_id = context.user_data.get('rejecting_transaction')
                if not transaction_id:
                    await update.message.reply_text("❌ تراکنشی برای رد یافت نشد.")
                    return
                    
                db = next(get_db())
                payment_manager = PaymentManager(db, self.application.bot)
                await payment_manager.reject_payment(update.effective_user.id, transaction_id, text)
                
                del context.user_data['waiting_for']
                del context.user_data['rejecting_transaction']
                
        # اگر در حال رد تراکنش هستیم
        elif 'rejecting_transaction' in context.user_data:
            transaction_id = context.user_data['rejecting_transaction']
            db = next(get_db())
            payment_manager = PaymentManager(db, self.application.bot)
            await payment_manager.reject_payment(update.effective_user.id, transaction_id, text)
            
            del context.user_data['rejecting_transaction']
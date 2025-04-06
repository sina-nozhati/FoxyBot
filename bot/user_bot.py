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
import asyncio

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
            f"👋 سلام <b>{user.first_name}</b>!\n\n"
            "🌟 به ربات <b>FoxyVPN</b> خوش آمدید.\n\n"
            "🔮 از طریق این ربات می‌توانید به راحتی:\n"
            "   🔹 اشتراک خریداری کنید\n"
            "   🔹 موجودی حساب خود را شارژ کنید\n"
            "   🔹 اطلاعات اشتراک‌های خود را مدیریت کنید"
        )
        
        # دکمه‌های منوی اصلی با طراحی شیشه‌ای و جذاب
        keyboard = [
            [
                InlineKeyboardButton("🛍️ فروشگاه اشتراک‌ها", callback_data="view_plans"),
            ],
            [
                InlineKeyboardButton("👤 پروفایل من", callback_data="view_profile"),
                InlineKeyboardButton("💎 شارژ کیف پول", callback_data="wallet_charge")
            ],
            [
                InlineKeyboardButton("📊 اشتراک‌های من", callback_data="view_subscriptions")
            ],
            [
                InlineKeyboardButton("🔍 راهنما", callback_data="help"),
                InlineKeyboardButton("💬 پشتیبانی", callback_data="support")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='HTML')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنما"""
        help_message = (
            "📚 <b>راهنمای استفاده از ربات</b>\n\n"
            
            "🛒 <b>خرید اشتراک:</b>\n"
            "برای خرید اشتراک، ابتدا باید کیف پول خود را شارژ کنید و سپس از منوی 'خرید اشتراک' پلن مورد نظر خود را انتخاب کنید.\n\n"
            
            "💰 <b>شارژ کیف پول:</b>\n"
            "برای شارژ کیف پول، مبلغ مورد نظر را به شماره کارت ارائه شده واریز کرده و تصویر رسید را ارسال کنید.\n\n"
            
            "📊 <b>اشتراک‌های من:</b>\n"
            "در این بخش می‌توانید اطلاعات اشتراک‌های فعال و غیرفعال خود را مشاهده کنید.\n\n"
            
            "👤 <b>پروفایل:</b>\n"
            "اطلاعات کاربری و موجودی کیف پول خود را در این بخش مشاهده کنید.\n\n"
            
            "📞 <b>پشتیبانی:</b>\n"
            "در صورت بروز هرگونه مشکل یا سوال، می‌توانید با پشتیبانی تماس بگیرید."
        )
        
        # دکمه بازگشت به منوی اصلی
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_message, reply_markup=reply_markup, parse_mode='HTML')

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
            f"✨ <b>پروفایل کاربری</b> ✨\n\n"
            f"👤 نام: {user.first_name} {user.last_name}\n"
            f"🆔 شناسه: <code>{user.telegram_id}</code>\n"
            f"💎 موجودی: <code>{user.wallet_balance:,}</code> تومان\n"
            f"📦 اشتراک فعال: <code>{len(active_subscriptions)}</code> عدد\n"
        )
        
        # دکمه‌های پروفایل با طراحی شیشه‌ای و جذاب
        keyboard = [
            [
                InlineKeyboardButton("💳 شارژ کیف پول", callback_data="wallet_charge")
            ],
            [
                InlineKeyboardButton("📱 اشتراک‌های من", callback_data="view_subscriptions"),
                InlineKeyboardButton("🛒 خرید اشتراک", callback_data="view_plans")
            ],
            [
                InlineKeyboardButton("📋 تاریخچه تراکنش‌ها", callback_data="transaction_history")
            ],
            [
                InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

    async def list_plans_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست پلن‌ها"""
        db = next(get_db())
        plans = crud.get_active_plans(db)
        
        if not plans:
            # ایجاد پلن‌های پیش‌فرض
            for plan_data in DEFAULT_PLANS:
                crud.create_plan(db, **plan_data)
            plans = crud.get_active_plans(db)
        
        message = "🛍️ <b>فروشگاه اشتراک‌ها</b>\n\n"
        
        # ایجاد دکمه‌های خرید با طراحی شیشه‌ای
        keyboard = []
        
        for plan in plans:
            plan_message = (
                f"✨ <b>{plan.name}</b>\n"
                f"📝 {plan.description}\n"
                f"⏳ مدت زمان: <code>{plan.duration_days}</code> روز\n"
                f"📊 ترافیک: <code>{plan.traffic_gb}</code> گیگابایت\n"
                f"💰 قیمت: <code>{plan.price:,}</code> تومان\n\n"
            )
            message += plan_message
            
            keyboard.append([
                InlineKeyboardButton(
                    f"✨ خرید پلن {plan.name} ✨",
                    callback_data=f"buy_plan_{plan.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

    async def list_subscriptions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش لیست اشتراک‌ها"""
        db = next(get_db())
        subscriptions = crud.get_user_subscriptions(db, update.effective_user.id)
        
        if not subscriptions:
            # دکمه‌های خرید اشتراک
            keyboard = [
                [InlineKeyboardButton("🛒 خرید اشتراک", callback_data="view_plans")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ شما هیچ اشتراکی ندارید.\n\n"
                "برای خرید اشتراک، از دکمه زیر استفاده کنید:",
                reply_markup=reply_markup
            )
            return
        
        message = "📊 <b>اشتراک‌های شما</b>\n\n"
        
        active_subs = [s for s in subscriptions if s.is_active]
        inactive_subs = [s for s in subscriptions if not s.is_active]
        
        if active_subs:
            message += "✅ <b>اشتراک‌های فعال:</b>\n\n"
            
            for sub in active_subs:
                # محاسبه درصد استفاده از ترافیک
                traffic_percent = int((sub.traffic_used / sub.plan.traffic_gb) * 100) if sub.plan.traffic_gb > 0 else 0
                # محاسبه روزهای باقی‌مانده
                days_left = (sub.end_date - datetime.now()).days
                
                message += (
                    f"📦 <b>{sub.plan.name}</b>\n"
                    f"🆔 شناسه: <code>{sub.id}</code>\n"
                    f"📅 تاریخ انقضا: <code>{sub.end_date.strftime('%Y-%m-%d')}</code> ({days_left} روز)\n"
                    f"📊 ترافیک: <code>{sub.traffic_used:.2f}</code> از <code>{sub.plan.traffic_gb}</code> GB ({traffic_percent}%)\n\n"
                )
                
                # ایجاد دکمه‌های مدیریت اشتراک
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📥 دریافت کانفیگ",
                            callback_data=f"get_config_{sub.id}"
                        ),
                        InlineKeyboardButton(
                            "🔄 تمدید",
                            callback_data=f"renew_sub_{sub.id}"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                message = ""  # پاک کردن پیام برای اشتراک بعدی
        
        if inactive_subs and not active_subs:
            message += "❌ <b>اشتراک‌های غیرفعال:</b>\n\n"
            
            for sub in inactive_subs[:3]:  # نمایش حداکثر 3 اشتراک غیرفعال
                message += (
                    f"📦 {sub.plan.name}\n"
                    f"🆔 شناسه: <code>{sub.id}</code>\n"
                    f"📅 تاریخ انقضا: <code>{sub.end_date.strftime('%Y-%m-%d')}</code>\n"
                    f"📊 ترافیک: <code>{sub.traffic_used:.2f}</code> از <code>{sub.plan.traffic_gb}</code> GB\n\n"
                )
            
            # دکمه‌های خرید اشتراک جدید
            keyboard = [
                [InlineKeyboardButton("🛒 خرید اشتراک جدید", callback_data="view_plans")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
        elif not active_subs:
            # دکمه‌های خرید اشتراک
            keyboard = [
                [InlineKeyboardButton("🛒 خرید اشتراک", callback_data="view_plans")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📊 <b>اشتراک‌های شما</b>\n\n"
                "❌ شما هیچ اشتراک فعالی ندارید.\n\n"
                "برای خرید اشتراک، از دکمه زیر استفاده کنید:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور نمایش موجودی و تراکنش‌ها"""
        db = next(get_db())
        user = crud.get_user(db, update.effective_user.id)
        
        if not user:
            await update.message.reply_text("❌ خطا در دریافت اطلاعات کاربر.")
            return
        
        message = (
            f"💎 <b>کیف پول دیجیتال شما</b>\n\n"
            f"👤 کاربر: {user.first_name} {user.last_name}\n"
            f"💰 موجودی: <code>{user.wallet_balance:,}</code> تومان\n\n"
            "🔷 <b>راهنمای شارژ کیف پول</b>\n"
            "1️⃣ مبلغ دلخواه را به شماره کارت زیر واریز کنید:\n"
            f"🔢 <code>{PAYMENT_CARD_NUMBER}</code>\n\n"
            "2️⃣ تصویر رسید پرداخت را ارسال نمایید.\n\n"
            "3️⃣ پس از تأیید توسط ادمین، مبلغ به کیف پول شما اضافه خواهد شد."
        )
        
        # ایجاد دکمه‌های مدیریت کیف پول با طراحی شیشه‌ای و جذاب
        keyboard = [
            [
                InlineKeyboardButton("📸 ارسال رسید پرداخت", callback_data="send_receipt")
            ],
            [
                InlineKeyboardButton("📊 تاریخچه تراکنش‌ها", callback_data="transaction_history"),
                InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_wallet")
            ],
            [
                InlineKeyboardButton("🛒 خرید با موجودی فعلی", callback_data="view_plans")
            ],
            [
                InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")
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
        
        if data == "back_to_main":
            # بازگشت به منوی اصلی
            await self.start_command(update, context)
            
        elif data == "view_plans":
            # نمایش لیست پلن‌ها
            await self.list_plans_command(update, context)
            
        elif data == "view_profile":
            # نمایش پروفایل
            await self.profile_command(update, context)
            
        elif data == "wallet_charge":
            # شارژ کیف پول
            await self.wallet_command(update, context)
            
        elif data == "view_subscriptions":
            # نمایش اشتراک‌ها
            await self.list_subscriptions_command(update, context)
            
        elif data == "help":
            # نمایش راهنما
            await self.help_command(update, context)
            
        elif data == "support":
            # ارتباط با پشتیبانی
            message = (
                "📞 <b>پشتیبانی</b>\n\n"
                "برای ارتباط با پشتیبانی، می‌توانید از روش‌های زیر استفاده کنید:\n\n"
                "1️⃣ ارسال پیام به ادمین: @admin_username\n"
                "2️⃣ ایمیل: support@example.com\n"
                "3️⃣ کانال اطلاع‌رسانی: @channel_username\n\n"
                "⏱ زمان پاسخگویی: 9 صبح تا 9 شب"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
        elif data.startswith("buy_plan_"):
            plan_id = int(data.split("_")[2])
            db = next(get_db())
            
            # دریافت اطلاعات پلن و کاربر
            plan = db.query(models.Plan).get(plan_id)
            user = crud.get_user(db, query.from_user.id)
            
            if not plan or not user:
                await query.message.reply_text("❌ خطا در دریافت اطلاعات.")
                return
            
            # بررسی موجودی
            if user.wallet_balance < plan.price:
                message = (
                    f"❌ <b>موجودی ناکافی</b>\n\n"
                    f"💰 موجودی شما: <code>{user.wallet_balance:,}</code> تومان\n"
                    f"💰 قیمت پلن: <code>{plan.price:,}</code> تومان\n"
                    f"💰 کسری موجودی: <code>{plan.price - user.wallet_balance:,}</code> تومان\n\n"
                    "لطفاً ابتدا کیف پول خود را شارژ کنید."
                )
                
                keyboard = [
                    [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_charge")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="view_plans")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML')
                return
            
            # نمایش تأیید خرید
            message = (
                f"🛒 <b>تأیید خرید</b>\n\n"
                f"📦 پلن: <b>{plan.name}</b>\n"
                f"⏱ مدت زمان: <code>{plan.duration_days}</code> روز\n"
                f"📊 ترافیک: <code>{plan.traffic_gb}</code> گیگابایت\n"
                f"💰 قیمت: <code>{plan.price:,}</code> تومان\n\n"
                f"💰 موجودی فعلی: <code>{user.wallet_balance:,}</code> تومان\n"
                f"💰 موجودی پس از خرید: <code>{user.wallet_balance - plan.price:,}</code> تومان\n\n"
                "آیا از خرید این پلن اطمینان دارید؟"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ تأیید و خرید", callback_data=f"confirm_buy_{plan_id}"),
                    InlineKeyboardButton("❌ انصراف", callback_data="view_plans")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
        elif data.startswith("confirm_buy_"):
            plan_id = int(data.split("_")[2])
            db = next(get_db())
            
            # دریافت اطلاعات پلن و کاربر
            plan = db.query(models.Plan).get(plan_id)
            user = crud.get_user(db, query.from_user.id)
            
            if not plan or not user:
                await query.message.reply_text("❌ خطا در دریافت اطلاعات.")
                return
            
            # بررسی مجدد موجودی
            if user.wallet_balance < plan.price:
                await query.message.edit_text(
                    "❌ موجودی شما کافی نیست.\n"
                    "لطفاً ابتدا موجودی خود را افزایش دهید."
                )
                return
            
            # ایجاد تراکنش و کم کردن از موجودی کاربر
            transaction = crud.create_transaction(
                db,
                user_id=user.id,
                amount=-plan.price,
                description=f"خرید پلن {plan.name}",
                status=models.TransactionStatus.COMPLETED
            )
            
            # کم کردن از موجودی کاربر
            crud.update_user_wallet(db, user.id, -plan.price)
            
            # ایجاد اشتراک جدید
            subscription = crud.create_subscription(
                db,
                user_id=user.id,
                plan_id=plan.id,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=plan.duration_days),
                is_active=True
            )
            
            # ارسال پیام موفقیت
            message = (
                f"✅ <b>خرید موفقیت‌آمیز</b>\n\n"
                f"📦 پلن: <b>{plan.name}</b>\n"
                f"⏱ مدت زمان: <code>{plan.duration_days}</code> روز\n"
                f"📊 ترافیک: <code>{plan.traffic_gb}</code> گیگابایت\n"
                f"📅 تاریخ انقضا: <code>{subscription.end_date.strftime('%Y-%m-%d')}</code>\n\n"
                f"💰 موجودی فعلی: <code>{user.wallet_balance:,}</code> تومان\n\n"
                "برای دریافت کانفیگ، از منوی 'اشتراک‌های من' اقدام کنید."
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("📥 دریافت کانفیگ", callback_data=f"get_config_{subscription.id}"),
                    InlineKeyboardButton("📊 اشتراک‌های من", callback_data="view_subscriptions")
                ],
                [
                    InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML')
            
        elif data.startswith("get_config_"):
            subscription_id = int(data.split("_")[2])
            db = next(get_db())
            
            # دریافت اطلاعات اشتراک
            subscription = db.query(models.Subscription).get(subscription_id)
            
            if not subscription or subscription.user.telegram_id != query.from_user.id:
                await query.message.reply_text("❌ خطا در دریافت اطلاعات اشتراک.")
                return
            
            # دریافت پنل
            panels = crud.get_active_panels(db)
            if not panels:
                await query.message.reply_text("❌ خطا در دریافت پنل.")
                return
            
            panel = panels[0]  # انتخاب اولین پنل فعال
            hiddify = HiddifyAPI(panel.domain, panel.proxy_path, panel.api_key)
            
            # ایجاد کاربر در هیدیفای یا بروزرسانی آن
            user_data = {
                "name": f"t{query.from_user.id}",
                "usage_limit_GB": subscription.plan.traffic_gb,
                "package_days": subscription.plan.duration_days,
                "comment": f"Telegram User: {query.from_user.first_name} {query.from_user.last_name}",
                "enable": True
            }
            
            try:
                # چک کردن وجود کاربر در هیدیفای
                hiddify_users = hiddify.get_all_users()
                hiddify_user = None
                
                for h_user in hiddify_users:
                    if h_user.get("name") == f"t{query.from_user.id}":
                        hiddify_user = h_user
                        break
                
                if hiddify_user:
                    # بروزرسانی کاربر
                    hiddify_user_uuid = hiddify_user.get("uuid")
                    hiddify.update_user(hiddify_user_uuid, user_data)
                else:
                    # ایجاد کاربر جدید
                    hiddify_user = hiddify.create_user(user_data)
                    hiddify_user_uuid = hiddify_user.get("uuid")
                
                # دریافت پروفایل کاربر
                user_profile = hiddify.get_user_profile(hiddify_user_uuid)
                
                # دریافت لینک‌های کانفیگ
                user_configs = hiddify.get_user_configs(hiddify_user_uuid)
                
                # دریافت آدرس کوتاه
                short_url = hiddify.get_user_short_url(hiddify_user_uuid)
                
                # دریافت اپلیکیشن‌ها
                user_apps = hiddify.get_user_apps(hiddify_user_uuid)
                
                # ارسال لینک کوتاه
                message = (
                    f"📥 <b>اطلاعات اشتراک شما</b>\n\n"
                    f"📦 پلن: <b>{subscription.plan.name}</b>\n"
                    f"⏱ مدت زمان: <code>{subscription.plan.duration_days}</code> روز\n"
                    f"📊 ترافیک: <code>{user_profile.get('usage_current_GB', 0):.2f}</code> از <code>{subscription.plan.traffic_gb}</code> گیگابایت\n"
                    f"📅 تاریخ انقضا: <code>{subscription.end_date.strftime('%Y-%m-%d')}</code>\n\n"
                    f"🔗 <b>لینک اشتراک:</b>\n<code>{short_url.get('short_url')}</code>\n\n"
                    "📱 <b>اپلیکیشن‌های پیشنهادی:</b>\n"
                )
                
                if user_apps:
                    for app in user_apps[:3]:  # ارسال 3 اپلیکیشن اول
                        message += f"- <a href='{app.get('link')}'>{app.get('name')}</a>\n"
                
                keyboard = [
                    [
                        InlineKeyboardButton("📱 دریافت اپلیکیشن‌ها", callback_data=f"get_apps_{subscription_id}"),
                        InlineKeyboardButton("📋 همه کانفیگ‌ها", callback_data=f"all_configs_{subscription_id}")
                    ],
                    [
                        InlineKeyboardButton("🔙 بازگشت", callback_data="view_subscriptions")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML', disable_web_page_preview=True)
                
            except Exception as e:
                logger.error(f"Error getting configs: {e}")
                await query.message.edit_text(
                    f"❌ خطا در دریافت کانفیگ: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="view_subscriptions")]])
                )
                
        elif data == "send_receipt":
            # آماده‌سازی برای دریافت رسید
            await query.message.edit_text(
                "📸 <b>ارسال رسید پرداخت</b>\n\n"
                "لطفاً تصویر رسید پرداخت خود را ارسال کنید.\n"
                "پس از بررسی توسط ادمین، مبلغ به کیف پول شما اضافه خواهد شد.",
                parse_mode='HTML'
            )
            context.user_data['waiting_for_receipt'] = True
            
        elif data == "refresh_profile":
            # بروزرسانی پروفایل
            await self.profile_command(update, context)
            
        elif data.startswith("transaction_history"):
            # نمایش تاریخچه تراکنش‌ها
            db = next(get_db())
            user = db.query(models.User).filter(models.User.telegram_id == query.from_user.id).first()
            
            if not user:
                await query.message.edit_text("❌ خطا در دریافت اطلاعات کاربر.")
                return
            
            # دریافت تراکنش‌های کاربر
            transactions = db.query(models.Transaction).filter(
                models.Transaction.user_id == user.id
            ).order_by(models.Transaction.created_at.desc()).limit(10).all()
            
            if not transactions:
                message = (
                    "📊 <b>تاریخچه تراکنش‌ها</b>\n\n"
                    "شما هیچ تراکنشی ندارید."
                )
                
                keyboard = [
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_charge")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML')
                return
            
            message = "📊 <b>تاریخچه تراکنش‌ها</b>\n\n"
            
            for transaction in transactions:
                status_emoji = {
                    models.TransactionStatus.PENDING: "⏳",
                    models.TransactionStatus.COMPLETED: "✅",
                    models.TransactionStatus.REJECTED: "❌",
                    models.TransactionStatus.CANCELLED: "🚫"
                }.get(transaction.status, "❓")
                
                transaction_type = "واریز" if transaction.amount > 0 else "برداشت"
                
                message += (
                    f"{status_emoji} <b>{transaction_type}</b>: <code>{abs(transaction.amount):,}</code> تومان\n"
                    f"📝 توضیحات: {transaction.description}\n"
                    f"⏰ تاریخ: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"📊 وضعیت: {transaction.status.value}\n\n"
                )
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_charge")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(message, reply_markup=reply_markup, parse_mode='HTML')

    async def handle_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش رسید پرداخت"""
        user_id = update.effective_user.id
        photo = update.message.photo[-1]  # بزرگترین سایز عکس
        
        # بررسی آیا کاربر در حالت ارسال رسید است
        if context.user_data.get('waiting_for_receipt'):
            # درخواست مبلغ واریزی
            await update.message.reply_text(
                "💰 لطفاً مبلغ واریزی را به تومان وارد کنید:\n"
                "مثال: 50000"
            )
            
            # ذخیره شناسه عکس در داده‌های کاربر
            context.user_data['receipt_photo_id'] = photo.file_id
            context.user_data['waiting_for_amount'] = True
            context.user_data['waiting_for_receipt'] = False
            
        else:
            # اگر کاربر در حالت ارسال رسید نیست، به او یادآوری کنیم
            keyboard = [
                [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet_charge")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📸 برای ارسال رسید پرداخت، ابتدا از منوی 'شارژ کیف پول' اقدام کنید.",
                reply_markup=reply_markup
            )

    async def run(self):
        """اجرای ربات"""
        try:
            # استفاده از روش آسنکرون مطابق با فرمت جدید کتابخانه python-telegram-bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=["message", "callback_query", "my_chat_member"])
            
            logger.info("User bot started successfully")
            
            # ادامه اجرا تا زمانی که سیگنال توقف دریافت شود
            stop_signal = asyncio.Future()
            await stop_signal
            
        except Exception as e:
            logger.error(f"Error starting User bot: {e}")
            
        finally:
            # پاکسازی منابع در صورت توقف ربات
            if self.application.is_initialized():
                await self.application.stop()
                await self.application.shutdown()
                logger.info("User bot has been shut down")
                
    def run_polling(self):
        """اجرای ربات در حالت polling (برای سازگاری با نسخه‌های قدیمی)"""
        try:
            self.application.run_polling()
        except Exception as e:
            logger.error(f"Error in run_polling: {e}") 
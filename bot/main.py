import logging
import os
import sys
import asyncio
from bot.admin_bot import AdminBot
from bot.user_bot import UserBot
from config import ADMIN_BOT_TOKEN, USER_BOT_TOKEN

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """تابع اصلی برای اجرای ربات‌ها"""
    try:
        logger.info("Starting FoxyVPN Telegram Bots...")
        
        # بررسی توکن‌های ربات
        if not ADMIN_BOT_TOKEN:
            logger.error("ADMIN_BOT_TOKEN is not set in environment variables!")
            sys.exit(1)
            
        if not USER_BOT_TOKEN:
            logger.error("USER_BOT_TOKEN is not set in environment variables!")
            sys.exit(1)
            
        logger.info(f"Admin Bot Token: {ADMIN_BOT_TOKEN[:6]}...{ADMIN_BOT_TOKEN[-6:]}")
        logger.info(f"User Bot Token: {USER_BOT_TOKEN[:6]}...{USER_BOT_TOKEN[-6:]}")
        
        # ایجاد نمونه‌های ربات
        logger.info("Initializing Admin Bot...")
        admin_bot = AdminBot()
        
        logger.info("Initializing User Bot...")
        user_bot = UserBot()
        
        # اجرای همزمان ربات‌ها
        logger.info("Starting both bots in polling mode...")
        
        # در نسخه 20 کتابخانه python-telegram-bot، باید از روش متفاوتی برای اجرای همزمان ربات‌ها استفاده کنیم
        # به جای asyncio.gather، دو تا ربات را به صورت مجزا اجرا می‌کنیم
        
        admin_app = admin_bot.application
        user_app = user_bot.application
        
        # اینیشیالایز کردن هر دو ربات
        await admin_app.initialize()
        await user_app.initialize()
        
        # شروع کردن پولینگ برای هر دو ربات
        await admin_app.start()
        await user_app.start()
        
        # استفاده از ساختار try-finally برای اطمینان از بسته شدن صحیح ربات‌ها
        try:
            # ماندن در حالت اجرا تا زمانی که کاربر کلید کنترل+C را فشار دهد
            await admin_app.updater.start_polling(allowed_updates=["message", "callback_query", "my_chat_member"])
            await user_app.updater.start_polling(allowed_updates=["message", "callback_query", "my_chat_member"])
            
            # ایجاد یک سیگنال برای توقف برنامه با کلید کنترل+C
            stop_signal = asyncio.Future()
            await stop_signal
            
        finally:
            # خاتمه دادن به هر دو ربات
            await admin_app.stop()
            await user_app.stop()
            
            # شات‌داون کردن نهایی
            await admin_app.shutdown()
            await user_app.shutdown()
        
    except Exception as e:
        logger.error(f"Error starting bots: {e}")
        raise

if __name__ == "__main__":
    # تنظیم مسیر Python برای import کردن ماژول‌ها
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # اجرای برنامه اصلی
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1) 
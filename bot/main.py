import logging
import os
import sys
import asyncio
import signal
from bot.admin_bot import AdminBot
from bot.user_bot import UserBot
from config import ADMIN_BOT_TOKEN, USER_BOT_TOKEN

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# سیگنال برای توقف برنامه
stop_event = asyncio.Event()

# تنظیم هندلر برای سیگنال‌های سیستمی
def signal_handler():
    """هندلر برای مدیریت سیگنال‌های سیستمی (مانند Ctrl+C)"""
    logger.info("Received stop signal! Shutting down...")
    stop_event.set()

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
        
        # تنظیم مدیریت سیگنال‌ها برای توقف نرم ربات‌ها
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(
                sig, signal_handler
            )
        
        # راه‌اندازی ربات‌های ادمین و کاربر به صورت همزمان
        admin_app = admin_bot.application
        user_app = user_bot.application
        
        # اینیشیالایز کردن ربات‌ها
        await admin_app.initialize()
        await user_app.initialize()
        
        # شروع ربات‌ها
        await admin_app.start()
        await user_app.start()
        
        # شروع پولینگ برای هر دو ربات
        await admin_app.updater.start_polling(
            allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"]
        )
        logger.info("Admin bot polling started successfully")
        
        await user_app.updater.start_polling(
            allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"]
        )
        logger.info("User bot polling started successfully")
        
        # انتظار برای سیگنال توقف
        logger.info("Both bots are running. Press Ctrl+C to stop.")
        await stop_event.wait()
        
    except Exception as e:
        logger.error(f"Error starting bots: {e}")
        logger.error(f"Fatal error: Cannot start bots. Check the token and internet connection.")
        sys.exit(1)
        
    finally:
        # متوقف کردن ربات‌ها در صورت وجود
        logger.info("Stopping bots...")
        try:
            # توقف و شات‌داون ربات‌ها
            if admin_app.is_initialized():
                await admin_app.stop()
                await admin_app.shutdown()
                
            if user_app.is_initialized():
                await user_app.stop()
                await user_app.shutdown()
                
            logger.info("Both bots have been shut down gracefully.")
        except Exception as e:
            logger.error(f"Error shutting down bots: {e}")

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
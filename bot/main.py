import logging
import asyncio
from admin_bot import AdminBot
from user_bot import UserBot

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """تابع اصلی برای اجرای ربات‌ها"""
    try:
        # ایجاد نمونه‌های ربات
        admin_bot = AdminBot()
        user_bot = UserBot()
        
        # اجرای همزمان ربات‌ها
        await asyncio.gather(
            admin_bot.application.run_polling(),
            user_bot.application.run_polling()
        )
        
    except Exception as e:
        logger.error(f"خطا در اجرای ربات‌ها: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 
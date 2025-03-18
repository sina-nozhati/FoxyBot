import sqlite3
import os
import logging

# تنظیم مسیر دیتابیس
USERS_DB_LOC = os.path.join(os.getcwd(), "Database", "hidyBot.db")

# تنظیم لاگ
LOG_DIR = os.path.join(os.getcwd(), "Logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    
LOG_LOC = os.path.join(LOG_DIR, "update_database.log")
logging.basicConfig(
    handlers=[logging.FileHandler(filename=LOG_LOC, encoding='utf-8', mode='a')],
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def update_database():
    """
    آپدیت ساختار دیتابیس و اضافه کردن فیلدهای مورد نیاز
    """
    print("در حال آپدیت دیتابیس...")
    logging.info("شروع آپدیت دیتابیس")
    
    try:
        # اتصال به دیتابیس
        conn = sqlite3.connect(USERS_DB_LOC)
        cur = conn.cursor()
        
        # افزودن فیلد banned به جدول users اگر وجود نداشته باشد
        try:
            # بررسی وجود ستون banned
            cur.execute("PRAGMA table_info(users)")
            columns = cur.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'banned' not in column_names:
                print("افزودن فیلد banned به جدول users")
                logging.info("افزودن فیلد banned به جدول users")
                cur.execute("ALTER TABLE users ADD COLUMN banned BOOLEAN DEFAULT 0")
                cur.execute("UPDATE users SET banned = 0")
                conn.commit()
                print("فیلد banned با موفقیت به جدول users اضافه شد")
                logging.info("فیلد banned با موفقیت به جدول users اضافه شد")
            else:
                print("فیلد banned از قبل در جدول users وجود دارد")
                logging.info("فیلد banned از قبل در جدول users وجود دارد")
                
            # بررسی وجود ستون proxy_path در جداول اشتراک
            cur.execute("PRAGMA table_info(order_subscriptions)")
            columns = cur.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'proxy_path' not in column_names:
                print("افزودن فیلد proxy_path به جدول order_subscriptions")
                logging.info("افزودن فیلد proxy_path به جدول order_subscriptions")
                cur.execute("ALTER TABLE order_subscriptions ADD COLUMN proxy_path TEXT")
                conn.commit()
                print("فیلد proxy_path با موفقیت به جدول order_subscriptions اضافه شد")
                logging.info("فیلد proxy_path با موفقیت به جدول order_subscriptions اضافه شد")
            else:
                print("فیلد proxy_path از قبل در جدول order_subscriptions وجود دارد")
                logging.info("فیلد proxy_path از قبل در جدول order_subscriptions وجود دارد")
                
            cur.execute("PRAGMA table_info(non_order_subscriptions)")
            columns = cur.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'proxy_path' not in column_names:
                print("افزودن فیلد proxy_path به جدول non_order_subscriptions")
                logging.info("افزودن فیلد proxy_path به جدول non_order_subscriptions")
                cur.execute("ALTER TABLE non_order_subscriptions ADD COLUMN proxy_path TEXT")
                conn.commit()
                print("فیلد proxy_path با موفقیت به جدول non_order_subscriptions اضافه شد")
                logging.info("فیلد proxy_path با موفقیت به جدول non_order_subscriptions اضافه شد")
            else:
                print("فیلد proxy_path از قبل در جدول non_order_subscriptions وجود دارد")
                logging.info("فیلد proxy_path از قبل در جدول non_order_subscriptions وجود دارد")
            
            # افزودن فیلد api_key به جدول servers اگر وجود نداشته باشد
            cur.execute("PRAGMA table_info(servers)")
            columns = cur.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'api_key' not in column_names:
                print("افزودن فیلد api_key به جدول servers")
                logging.info("افزودن فیلد api_key به جدول servers")
                cur.execute("ALTER TABLE servers ADD COLUMN api_key TEXT")
                conn.commit()
                print("فیلد api_key با موفقیت به جدول servers اضافه شد")
                logging.info("فیلد api_key با موفقیت به جدول servers اضافه شد")
            else:
                print("فیلد api_key از قبل در جدول servers وجود دارد")
                logging.info("فیلد api_key از قبل در جدول servers وجود دارد")
                
            # افزودن فیلد proxy_path به جدول servers اگر وجود نداشته باشد
            if 'proxy_path' not in column_names:
                print("افزودن فیلد proxy_path به جدول servers")
                logging.info("افزودن فیلد proxy_path به جدول servers")
                cur.execute("ALTER TABLE servers ADD COLUMN proxy_path TEXT")
                conn.commit()
                print("فیلد proxy_path با موفقیت به جدول servers اضافه شد")
                logging.info("فیلد proxy_path با موفقیت به جدول servers اضافه شد")
            else:
                print("فیلد proxy_path از قبل در جدول servers وجود دارد")
                logging.info("فیلد proxy_path از قبل در جدول servers وجود دارد")
                
        except sqlite3.Error as e:
            print(f"خطا در آپدیت جدول users: {e}")
            logging.error(f"خطا در آپدیت جدول users: {e}")
            return False
            
        # بستن اتصال
        conn.close()
        print("آپدیت دیتابیس با موفقیت انجام شد")
        logging.info("آپدیت دیتابیس با موفقیت انجام شد")
        return True
        
    except Exception as e:
        print(f"خطا در آپدیت دیتابیس: {e}")
        logging.error(f"خطا در آپدیت دیتابیس: {e}")
        return False

if __name__ == "__main__":
    update_database() 
import datetime
import json
import logging
import os
import sqlite3
from sqlite3 import Error
from version import is_version_less
#from urllib.parse import urlparse

#from Utils import api
#from config import PANEL_URL, API_PATH, USERS_DB_LOC




class UserDBManager:
    def __init__(self, db_file):
        self.conn = self.create_connection(db_file)
        self.create_user_table()
        #self.set_default_configs()

    #close connection
    def __del__(self):
        self.conn.close()
    
    def close(self):
        self.conn.close()
    

    def create_connection(self, db_file):
        """ Create a database connection to a SQLite database """
        try:
            conn = sqlite3.connect(db_file, check_same_thread=False)
            return conn
        except Error as e:
            logging.error(f"Error while connecting to database \n Error:{e}")
            return None

    def create_user_table(self):
        """Create tables for storing users, plans, and orders"""
        try:
            cur = self.conn.cursor()

            # Create users table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                is_blocked BOOLEAN DEFAULT FALSE,
                banned BOOLEAN DEFAULT FALSE,
                test_subscription BOOLEAN DEFAULT FALSE
            )
            """)

            # Create plans table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY,
                size_gb INTEGER NOT NULL,
                days INTEGER NOT NULL,
                price INTEGER NOT NULL,
                server_id INTEGER NOT NULL,
                description TEXT,
                status BOOLEAN DEFAULT TRUE
            )
            """)

            # Create orders table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                plan_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
                FOREIGN KEY (plan_id) REFERENCES plans (id)
            )
            """)
            
            # Create order subscriptions table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS order_subscriptions (
                id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL,
                uuid TEXT NOT NULL,
                server_id INTEGER NOT NULL,
                proxy_path TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
            """)
            
            # Create non_order subscriptions table for linking user's own configs
            cur.execute("""
            CREATE TABLE IF NOT EXISTS non_order_subscriptions (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER NOT NULL,
                uuid TEXT NOT NULL,
                server_id INTEGER NOT NULL,
                proxy_path TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
            """)
            
            # Create str_config table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS str_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)
            
            # Create int_config table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS int_config (
                key TEXT PRIMARY KEY,
                value INTEGER
            )
            """)
            
            # Create bool_config table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS bool_config (
                key TEXT PRIMARY KEY,
                value BOOLEAN
            )
            """)
            
            # Create wallet table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS wallet (
                telegram_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
            """)
            
            # Create payments table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER NOT NULL,
                payment_amount INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                payment_image TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
            """)
            
            # Create servers table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                proxy_path TEXT,
                api_key TEXT,
                user_limit INTEGER NOT NULL,
                title TEXT,
                description TEXT,
                status BOOLEAN DEFAULT TRUE,
                default_server BOOLEAN DEFAULT FALSE
            )
            """)

            # Check if proxy_path column exists in order_subscriptions, add if not exists
            try:
                cur.execute("SELECT proxy_path FROM order_subscriptions LIMIT 1")
            except Error:
                # Column doesn't exist, add it
                cur.execute("ALTER TABLE order_subscriptions ADD COLUMN proxy_path TEXT")
                print("Added proxy_path column to order_subscriptions table")
                
            # Check if proxy_path column exists in non_order_subscriptions, add if not exists
            try:
                cur.execute("SELECT proxy_path FROM non_order_subscriptions LIMIT 1")
            except Error:
                # Column doesn't exist, add it
                cur.execute("ALTER TABLE non_order_subscriptions ADD COLUMN proxy_path TEXT")
                print("Added proxy_path column to non_order_subscriptions table")
            
            self.conn.commit()
            print("User table created successfully!")
            logging.info("User table created successfully!")
        except Error as e:
            print(f"Error creating table: {e}")
            logging.error(f"Error creating table: {e}")
            return False
        return True

    def select_users(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM users")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all users \n Error:{e}")
            return None

    def find_user(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find user!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM users WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"User {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding user {kwargs} \n Error:{e}")
            return None

    def delete_user(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to delete user!")
            return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM users WHERE {key}=?", (value,))
                self.conn.commit()
            logging.info(f"User {kwargs} deleted successfully!")
            return True
        except Error as e:
            logging.error(f"Error while deleting user {kwargs} \n Error:{e}")
            return False

    def edit_user(self, telegram_id, **kwargs):
        cur = self.conn.cursor()

        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE users SET {key}=? WHERE telegram_id=?", (value, telegram_id))
                self.conn.commit()
                logging.info(f"User [{telegram_id}] successfully update [{key}] to [{value}]")
            except Error as e:
                logging.error(f"Error while updating user [{telegram_id}] [{key}] to [{value}] \n Error: {e}")
                return False

        return True

    def add_user(self, telegram_id, full_name,username, created_at):
        cur = self.conn.cursor()
        try:
            print(f"Adding user to database: telegram_id={telegram_id}, full_name={full_name}, username={username}, created_at={created_at}")
            cur.execute("INSERT INTO users(telegram_id, full_name,username, created_at) VALUES(?,?,?,?)",
                        (telegram_id, full_name,username, created_at))
            self.conn.commit()
            print(f"User [{telegram_id}] added successfully!")
            logging.info(f"User [{telegram_id}] added successfully!")
            return True

        except Error as e:
            print(f"Error while adding user [{telegram_id}] \n Error: {e}")
            logging.error(f"Error while adding user [{telegram_id}] \n Error: {e}")
            if "UNIQUE constraint failed" in str(e):
                # اگر کاربر قبلاً وجود داشته باشد
                print(f"User [{telegram_id}] already exists in database")
                return True
            return False

    def add_plan(self, plan_id, size_gb, days, price, server_id, description=None, status=True):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO plans(id,size_gb, days, price, server_id, description, status) VALUES(?,?,?,?,?,?,?)",
                        (plan_id, size_gb, days, price, server_id, description, status))
            self.conn.commit()
            logging.info(f"Plan [{size_gb}GB] added successfully!")
            return True

        except Error as e:
            logging.error(f"Error while adding plan [{size_gb}GB] \n Error: {e}")
            return False

    def select_plans(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM plans ORDER BY price ASC")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all plans \n Error:{e}")
            return None

    def find_plan(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find plan!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM plans WHERE {key}=? ORDER BY price ASC", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Plan {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding plan {kwargs} \n Error:{e}")
            return None

    def delete_plan(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to delete plan!")
            return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM plans WHERE {key}=?", (value,))
                self.conn.commit()
            logging.info(f"Plan {kwargs} deleted successfully!")
            return True
        except Error as e:
            logging.error(f"Error while deleting plan {kwargs} \n Error:{e}")
            return False

    def edit_plan(self, plan_id, **kwargs):
        cur = self.conn.cursor()

        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE plans SET {key}=? WHERE id=?", (value, plan_id))
                self.conn.commit()
                logging.info(f"Plan [{plan_id}] successfully update [{key}] to [{value}]")
            except Error as e:
                logging.error(f"Error while updating plan [{plan_id}] [{key}] to [{value}] \n Error: {e}")
                return False

        return True
    
    def add_user_plans(self, telegram_id, plan_id):
        cur = self.conn.cursor()
        try:
            cur.execute("INSERT INTO user_plans(telegram_id, plan_id) VALUES(?,?)",
                        (telegram_id, plan_id))
            self.conn.commit()
            logging.info(f"Plan [{plan_id}] Reserved for [{telegram_id}] successfully!")
            return True

        except Error as e:
            logging.error(f"Error while Reserving plan [{plan_id}] for [{telegram_id}] \n Error: {e}")
            return False

    def select_user_plans(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM user_plans")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all user_plans \n Error:{e}")
            return None

    def find_user_plans(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find user_plan!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM user_plans WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Plan {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding user_plans {kwargs} \n Error:{e}")
            return None

    def delete_user_plans(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to delete user_plan!")
            return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM user_plans WHERE {key}=?", (value,))
                self.conn.commit()
            logging.info(f"Plan {kwargs} deleted successfully!")
            return True
        except Error as e:
            logging.error(f"Error while deleting user_plans {kwargs} \n Error:{e}")
            return False

    def edit_user_plans(self, user_plans_id, **kwargs):
        cur = self.conn.cursor()

        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE user_plans SET {key}=? WHERE id=?", (value, user_plans_id))
                self.conn.commit()
                logging.info(f"user_plans [{user_plans_id}] successfully update [{key}] to [{value}]")
            except Error as e:
                logging.error(f"Error while updating user_plans [{user_plans_id}] [{key}] to [{value}] \n Error: {e}")
                return False

        return True
    
    def add_order(self, order_id, telegram_id,user_name, plan_id, created_at):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO orders(id,telegram_id, plan_id,user_name,created_at) VALUES(?,?,?,?,?)",
                (order_id, telegram_id, plan_id,user_name, created_at))
            self.conn.commit()
            logging.info(f"Order [{order_id}] added successfully!")
            return True

        except Error as e:
            logging.error(f"Error while adding order [{order_id}] \n Error: {e}")
            return False

    def select_orders(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM orders")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all orders \n Error:{e}")
            return None

    def find_order(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find order!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM orders WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Order {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding order {kwargs} \n Error:{e}")
            return None

    def edit_order(self, order_id, **kwargs):
        cur = self.conn.cursor()

        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE orders SET {key}=? WHERE id=?", (value, order_id))
                self.conn.commit()
                logging.info(f"Order [{order_id}] successfully update [{key}] to [{value}]")
            except Error as e:
                logging.error(f"Error while updating order [{order_id}] [{key}] to [{value}] \n Error: {e}")
                return False

        return True

    def add_order_subscription(self, sub_id, order_id, uuid, server_id):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO order_subscriptions(id,order_id,uuid,server_id) VALUES(?,?,?,?)",
                (sub_id, order_id, uuid, server_id))
            self.conn.commit()
            logging.info(f"Order [{order_id}] added successfully!")
            return True

        except Error as e:
            logging.error(f"Error while adding order [{order_id}] \n Error: {e}")
            return False

    def select_order_subscription(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM order_subscriptions")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all orders \n Error:{e}")
            return None

    def find_order_subscription(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find order!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM order_subscriptions WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Order {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding order {kwargs} \n Error:{e}")
            return None

    def edit_order_subscriptions(self, order_id, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE order_subscriptions SET {key}=? WHERE order_id=?", (value, order_id))
                self.conn.commit()
                return True
            except Error as e:
                logging.error(f"Error while editing order_subscriptions [{order_id}] \n Error:{e}")
                return False
        return False

    def update_subscription_proxy_path(self, subscription_type, identifier, uuid, proxy_path):
        """
        بروزرسانی مسیر پروکسی کاربر در جدول اشتراک‌ها
        
        Args:
            subscription_type: نوع اشتراک ('order' یا 'non_order')
            identifier: شناسه اشتراک (order_id یا telegram_id)
            uuid: UUID کاربر
            proxy_path: مسیر پروکسی کاربر
            
        Returns:
            bool: نتیجه عملیات
        """
        cur = self.conn.cursor()
        try:
            if subscription_type == 'order':
                cur.execute("UPDATE order_subscriptions SET proxy_path=? WHERE order_id=? AND uuid=?", 
                           (proxy_path, identifier, uuid))
            elif subscription_type == 'non_order':
                cur.execute("UPDATE non_order_subscriptions SET proxy_path=? WHERE telegram_id=? AND uuid=?",
                           (proxy_path, identifier, uuid))
            else:
                return False
                
            self.conn.commit()
            print(f"Updated proxy_path for {subscription_type} subscription [ID: {identifier}, UUID: {uuid}] to {proxy_path}")
            return True
        except Error as e:
            print(f"Error updating proxy_path for {subscription_type} subscription: {e}")
            return False
            
    def get_subscription_proxy_path(self, subscription_type, identifier, uuid):
        """
        دریافت مسیر پروکسی کاربر از جدول اشتراک‌ها
        
        Args:
            subscription_type: نوع اشتراک ('order' یا 'non_order')
            identifier: شناسه اشتراک (order_id یا telegram_id)
            uuid: UUID کاربر
            
        Returns:
            str: مسیر پروکسی کاربر یا None در صورت عدم وجود
        """
        cur = self.conn.cursor()
        try:
            if subscription_type == 'order':
                cur.execute("SELECT proxy_path FROM order_subscriptions WHERE order_id=? AND uuid=?", 
                           (identifier, uuid))
            elif subscription_type == 'non_order':
                cur.execute("SELECT proxy_path FROM non_order_subscriptions WHERE telegram_id=? AND uuid=?",
                           (identifier, uuid))
            else:
                return None
                
            result = cur.fetchone()
            if result and result[0]:
                return result[0]
            return None
        except Error as e:
            print(f"Error getting proxy_path for {subscription_type} subscription: {e}")
            return None

    def delete_order_subscription(self, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM order_subscriptions WHERE {key}=?", (value,))
                self.conn.commit()
                logging.info(f"Order [{value}] deleted successfully!")
            return True
        except Error as e:
            logging.error(f"Error while deleting order [{kwargs}] \n Error: {e}")
            return False

    def add_non_order_subscription(self, non_sub_id, telegram_id, uuid, server_id):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO non_order_subscriptions(id,telegram_id,uuid,server_id) VALUES(?,?,?,?)",
                (non_sub_id, telegram_id, uuid, server_id))
            self.conn.commit()
            logging.info(f"Order [{telegram_id}] added successfully!")
            return True

        except Error as e:
            logging.error(f"Error while adding order [{telegram_id}] \n Error: {e}")
            return False

    def select_non_order_subscriptions(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM non_order_subscriptions")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all orders \n Error:{e}")
            return None

    def find_non_order_subscription(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find order!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM non_order_subscriptions WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Order {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding order {kwargs} \n Error:{e}")
            return None

    def delete_non_order_subscription(self, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM non_order_subscriptions WHERE {key}=?", (value,))
                self.conn.commit()
                logging.info(f"Order [{value}] deleted successfully!")
            return True
        except Error as e:
            logging.error(f"Error while deleting order [{kwargs}] \n Error: {e}")
            return False

    def edit_bool_config(self, key_row, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE bool_config SET {key}=? WHERE key=?", (value, key_row))
                self.conn.commit()
                logging.info(f"Settings [{key}] successfully update [{key}] to [{value}]")
            except Error as e:
                logging.error(f"Error while updating settings [{key}] [{key}] to [{value}] \n Error: {e}")
                return False

        return True

    def find_bool_config(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find settings!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM bool_config WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Settings {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding settings {kwargs} \n Error:{e}")
            return None

    def add_bool_config(self, key, value):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT or IGNORE INTO bool_config(key,value) VALUES(?,?)",
                (key, value))
            self.conn.commit()
            logging.info(f"Settings [{key}] added successfully!")
            return True
        except Error as e:
            logging.error(f"Error while adding settings [{key}] \n Error: {e}")
            return False
        finally:
            cur.close()
            

    def select_bool_config(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM bool_config")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all settings \n Error:{e}")
            return None

    def select_str_config(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM str_config")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all settings \n Error:{e}")
            return None

    def find_str_config(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find settings!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM str_config WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Settings {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding settings {kwargs} \n Error:{e}")
            return None

    def edit_str_config(self, key_row, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():
            try:
                cur.execute(f"UPDATE str_config SET {key}=? WHERE key=?", (value, key_row))
                self.conn.commit()
                logging.info(f"Settings [{key}] successfully update [{key}] to [{value}]")
            except Error as e:
                logging.error(f"Error while updating settings [{key}] [{key}] to [{value}] \n Error: {e}")
                return False

        return True

    def add_str_config(self, key, value):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT or IGNORE INTO str_config(key,value) VALUES(?,?)",
                (key, value))
            self.conn.commit()
            logging.info(f"Settings [{key}] added successfully!")
            return True
        except Error as e:
            logging.error(f"Error while adding settings [{key}] \n Error: {e}")
            return False
        finally:
            cur.close()

    def select_int_config(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM int_config")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all settings \n Error:{e}")
            return None

    def find_int_config(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find settings!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM int_config WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Settings {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding settings {kwargs} \n Error:{e}")
            return None
    def edit_int_config(self, key_row, **kwargs):
        cur = self.conn.cursor()
        for key, value in kwargs.items():            
            try:
                cur.execute(f"UPDATE int_config SET {key}=? WHERE key=?", (value, key_row))
                self.conn.commit()
                logging.info(f"Settings [{key}] successfully update [{key}] to [{value}]")
            except Error as e:
                logging.error(f"Error while updating settings [{key}] [{key}] to [{value}] \n Error: {e}")
                return False

        return True

    def add_int_config(self, key, value):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT or IGNORE INTO int_config(key,value) VALUES(?,?)",
                (key, value))
            self.conn.commit()
            logging.info(f"Settings [{key}] added successfully!")
            return True
        except Error as e:
            logging.error(f"Error while adding settings [{key}] \n Error: {e}")
            return False
        finally:
            cur.close()

    def set_default_configs(self):
        # اطمینان از وجود کاربر ادمین در دیتابیس
        admin_ids = self.find_str_config(key="bot_admin_id")
        if admin_ids and admin_ids['value']:
            try:
                admin_list = json.loads(admin_ids['value'])
                for admin_id in admin_list:
                    if not self.find_user(telegram_id=admin_id):
                        print(f"Adding admin user {admin_id} to database")
                        self.add_user(
                            telegram_id=admin_id,
                            full_name="Admin",
                            username="admin",
                            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
            except json.JSONDecodeError:
                print(f"Error parsing admin IDs: {admin_ids['value']}")
            except Exception as e:
                print(f"Error adding admin user: {str(e)}")
        
        self.add_bool_config("visible_hiddify_hyperlink", True)
        self.add_bool_config("three_random_num_price", False)
        self.add_bool_config("force_join_channel", False)
        self.add_bool_config("panel_auto_backup", True)
        self.add_bool_config("bot_auto_backup", True)
        self.add_bool_config("test_subscription", True)
        self.add_bool_config("reminder_notification", True)
        
        self.add_bool_config("renewal_subscription_status", True)
        self.add_bool_config("buy_subscription_status", True)


        self.add_bool_config("visible_conf_dir", False)
        self.add_bool_config("visible_conf_sub_auto", True)
        self.add_bool_config("visible_conf_sub_url", False)
        self.add_bool_config("visible_conf_sub_url_b64", False)
        self.add_bool_config("visible_conf_clash", False)
        self.add_bool_config("visible_conf_hiddify", False)
        self.add_bool_config("visible_conf_sub_sing_box", False)
        self.add_bool_config("visible_conf_sub_full_sing_box", False)

        self.add_str_config("bot_admin_id", None)
        self.add_str_config("bot_token_admin", None)
        self.add_str_config("bot_token_client", None)
        self.add_str_config("bot_lang", None)

        self.add_str_config("card_number", None)
        self.add_str_config("card_holder", None)
        self.add_str_config("support_username", None)
        self.add_str_config("channel_id", None)
        self.add_str_config("msg_user_start", None)

        self.add_str_config("msg_manual_android", None)
        self.add_str_config("msg_manual_ios", None)
        self.add_str_config("msg_manual_windows", None)
        self.add_str_config("msg_manual_mac", None)
        self.add_str_config("msg_manual_linux", None)

        self.add_str_config("msg_faq", None)

        self.add_int_config("min_deposit_amount", 10000)

        self.add_int_config("reminder_notification_days", 3)
        self.add_int_config("reminder_notification_usage", 3)

        self.add_int_config("test_sub_days", 1)
        self.add_int_config("test_sub_size_gb", 1)
        
        self.add_int_config("advanced_renewal_days", 3)
        self.add_int_config("advanced_renewal_usage", 3)
        
        self.add_int_config("renewal_method", 1)



    def add_wallet(self, telegram_id):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO wallet(telegram_id) VALUES(?)",
                (telegram_id,))
            self.conn.commit()
            logging.info(f"Balance [{telegram_id}] added successfully!")
            return True

        except Error as e:
            logging.error(f"Error while adding balance [{telegram_id}] \n Error: {e}")
            return False

    def select_wallet(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM wallet")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all balance \n Error:{e}")
            return None

    def find_wallet(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find balance!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM wallet WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Balance {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding balance {kwargs} \n Error:{e}")
            return None

    def edit_wallet(self, telegram_id, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"UPDATE wallet SET {key}=? WHERE telegram_id=?", (value, telegram_id,))
                self.conn.commit()
                logging.info(f"balance successfully update [{key}] to [{value}]")
            return True
        except Error as e:
            logging.error(f"Error while updating balance [{key}] to [{value}] \n Error: {e}")
            return False

    def add_payment(self, payment_id, telegram_id, payment_amount, payment_method, payment_image, created_at):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO payments(id,telegram_id, payment_amount,payment_method,payment_image,created_at) VALUES(?,?,?,?,?,?)",
                (payment_id, telegram_id, payment_amount, payment_method, payment_image, created_at))
            self.conn.commit()
            logging.info(f"Payment [{payment_id}] added successfully!")
            return True

        except Error as e:
            logging.error(f"Error while adding payment [{payment_id}] \n Error: {e}")
            return False

    def edit_payment(self, payment_id, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"UPDATE payments SET {key}=? WHERE id=?", (value, payment_id))
                self.conn.commit()
                logging.info(f"payment successfully update [{key}] to [{value}]")
            return True
        except Error as e:
            logging.error(f"Error while updating payment [{key}] to [{value}] \n Error: {e}")
            return False

    def find_payment(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find payment!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM payments WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Payment {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding payment {kwargs} \n Error:{e}")
            return None
        
    def select_payments(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM payments")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all payments \n Error:{e}")
            return None
    
    def select_servers(self):
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM servers")
            rows = cur.fetchall()
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while selecting all servers \n Error:{e}")
            return None
        
    def add_server(self, url, user_limit, title=None, description=None, status=True, default_server=False):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO servers(url,title,description,user_limit,status,default_server) VALUES(?,?,?,?,?,?)",
                (url, title, description, user_limit, status, default_server))
            self.conn.commit()
            logging.info(f"Server [{url}] added successfully!")
            return True
        except Error as e:
            logging.error(f"Error while adding server [{url}] \n Error: {e}")
            return False
    
    def edit_server(self, server_id, **kwargs):
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"UPDATE servers SET {key}=? WHERE id=?", (value, server_id))
                self.conn.commit()
                logging.info(f"Server [{server_id}] successfully update [{key}] to [{value}]")
            return True
        except Error as e:
            logging.error(f"Error while updating server [{server_id}] [{key}] to [{value}] \n Error: {e}")
            return False
    
    def find_server(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to find server!")
            return None
        rows = []
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"SELECT * FROM servers WHERE {key}=?", (value,))
                rows = cur.fetchall()
            if len(rows) == 0:
                logging.info(f"Server {kwargs} not found!")
                return None
            rows = [dict(zip([key[0] for key in cur.description], row)) for row in rows]
            return rows
        except Error as e:
            logging.error(f"Error while finding server {kwargs} \n Error:{e}")
            return None
        
    def delete_server(self, **kwargs):
        if len(kwargs) != 1:
            logging.warning("You can only use one key to delete server!")
            return False
        cur = self.conn.cursor()
        try:
            for key, value in kwargs.items():
                cur.execute(f"DELETE FROM servers WHERE {key}=?", (value,))
                self.conn.commit()
            logging.info(f"server {kwargs} deleted successfully!")
            return True
        except Error as e:
            logging.error(f"Error while deleting server {kwargs} \n Error:{e}")
            return False
        
    
    def backup_to_json(self, backup_dir):
        try:

            backup_data = {}  # Store backup data in a dictionary

            # List of tables to backup
            tables = ['users', 'plans', 'orders', 'order_subscriptions', 'non_order_subscriptions',
                      'str_config', 'int_config', 'bool_config', 'wallet', 'payments', 'servers']

            for table in tables:
                cur = self.conn.cursor()
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()

                # Convert rows to list of dictionaries
                table_data = []
                for row in rows:
                    columns = [column[0] for column in cur.description]
                    table_data.append(dict(zip(columns, row)))

                backup_data[table] = table_data
            return backup_data

        except sqlite3.Error as e:
            logging.error('SQLite error:', str(e))
            return False
    def restore_from_json(self, backup_file):
        logging.info(f"Restoring database from {backup_file}...")
        try:
            cur = self.conn.cursor()

            with open(backup_file, 'r') as json_file:
                backup_data = json.load(json_file)
                
            if not isinstance(backup_data, dict):
                logging.error('Backup data should be a dictionary.')
                print('Backup data should be a dictionary.')
                return
            # print(backup_data.get('version'), VERSION)
            # if backup_data.get('version') != VERSION:
            #     if backup_data.get('version') is None:
            #         logging.error('Backup data version is not found.')
            #         print('Backup data version is not found.')
            #         return
            #     if VERSION.find('-pre'):
            #         VERSION = VERSION.split('-pre')[0]
            #     if is_version_less(backup_data.get('version'),VERSION ):
            #         logging.error('Backup data version is less than current version.')
            #         print('Backup data version is less than current version.')
            #         if is_version_less(backup_data.get('version'), '5.5.0'):
            #             logging.error('Backup data version is less than 5.5.0.')
            #             print('Backup data version is less than 5.5.0.')
            #             return 

            self.conn.execute('BEGIN TRANSACTION')

            for table, data in backup_data.items():
                if table == 'version':
                    continue
                logging.info(f"Restoring table {table}...")
                for entry in data:
                    if not isinstance(entry, dict):
                        logging.error('Invalid entry format. Expected a dictionary.')
                        print('Invalid entry format. Expected a dictionary.')
                        continue

                    keys = ', '.join(entry.keys())
                    placeholders = ', '.join(['?' for _ in entry.values()])
                    values = tuple(entry.values())
                    query = f"INSERT OR REPLACE INTO {table} ({keys}) VALUES ({placeholders})"
                    logging.info(f"Query: {query}")
                    
                    try:
                        cur.execute(query, values)
                    except sqlite3.Error as e:
                        logging.error('SQLite error:', str(e))
                        logging.error('Entry:', entry)
                        print('SQLite error:', str(e))
                        print('Entry:', entry)

            self.conn.commit()
            logging.info('Database restored successfully.')
            return True

        except sqlite3.Error as e:
            logging.error('SQLite error:', str(e))
            return False
    

USERS_DB_LOC = os.path.join(os.getcwd(), "Database", "hidyBot.db")
USERS_DB = UserDBManager(USERS_DB_LOC)

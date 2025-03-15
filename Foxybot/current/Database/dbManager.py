import sqlite3
import os
import json
from datetime import datetime
import uuid as uuid_lib

# Database file path
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Database", "hiddify_bot.db")

def init_db():
    """Initialize database tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        uuid TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        telegram_id INTEGER,
        wallet_balance INTEGER DEFAULT 0,
        has_free_test INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        days INTEGER NOT NULL,
        usage_limit_gb REAL NOT NULL,
        price INTEGER NOT NULL,
        server_id INTEGER,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create orders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_uuid TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT NOT NULL,
        transaction_id TEXT,
        payment_method TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_uuid) REFERENCES users (uuid),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')
    
    # Create payments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        user_uuid TEXT NOT NULL,
        amount INTEGER NOT NULL,
        method TEXT NOT NULL,
        status TEXT NOT NULL,
        transaction_id TEXT,
        screenshot_file_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (user_uuid) REFERENCES users (uuid)
    )
    ''')
    
    # Create servers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        proxy_path TEXT NOT NULL,
        api_key TEXT NOT NULL,
        user_limit INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    
    # Create backup table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_id TEXT,
        size INTEGER,
        type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def get_user_from_db(uuid):
    """Get user from database by UUID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

def get_user_by_telegram_id(telegram_id):
    """Get user from database by Telegram ID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

def add_user_to_db(uuid, name, telegram_id=None, wallet_balance=0):
    """Add user to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO users (uuid, name, telegram_id, wallet_balance) VALUES (?, ?, ?, ?)",
        (uuid, name, telegram_id, wallet_balance)
    )
    
    conn.commit()
    conn.close()

def update_user_wallet(uuid, wallet_balance):
    """Update user wallet balance"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    if user:
        # Update existing user
        cursor.execute(
            "UPDATE users SET wallet_balance = ? WHERE uuid = ?",
            (wallet_balance, uuid)
        )
    else:
        # Get user details from API and add to database
        from Utils.api import get_user, PROXY_PATH, API_KEY
        user_api = get_user(PROXY_PATH, API_KEY, uuid)
        if user_api:
            cursor.execute(
                "INSERT INTO users (uuid, name, wallet_balance) VALUES (?, ?, ?)",
                (uuid, user_api["name"], wallet_balance)
            )
    
    conn.commit()
    conn.close()

def link_user_subscription(telegram_id, uuid, name):
    """Link Telegram ID to user subscription"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    if user:
        # Update existing user
        cursor.execute(
            "UPDATE users SET telegram_id = ? WHERE uuid = ?",
            (telegram_id, uuid)
        )
    else:
        # Add new user
        cursor.execute(
            "INSERT INTO users (uuid, name, telegram_id) VALUES (?, ?, ?)",
            (uuid, name, telegram_id)
        )
    
    conn.commit()
    conn.close()

def unlink_user_subscription(telegram_id):
    """Unlink Telegram ID from user subscription"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET telegram_id = NULL WHERE telegram_id = ?",
        (telegram_id,)
    )
    
    conn.commit()
    conn.close()

def get_user_subscription(telegram_id):
    """Get user subscription by Telegram ID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

def add_product(name, description, days, usage_limit_gb, price, server_id=None):
    """Add product to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO products (name, description, days, usage_limit_gb, price, server_id) VALUES (?, ?, ?, ?, ?, ?)",
        (name, description, days, usage_limit_gb, price, server_id)
    )
    
    product_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return product_id

def get_product(product_id):
    """Get product from database by ID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    
    conn.close()
    
    if product:
        return dict(product)
    return None

def get_all_products(active_only=True):
    """Get all products"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY price ASC")
    else:
        cursor.execute("SELECT * FROM products ORDER BY price ASC")
    
    products = cursor.fetchall()
    
    conn.close()
    
    return [dict(product) for product in products]

def update_product(product_id, data):
    """Update product in database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Build SET clause dynamically
    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values())
    values.append(product_id)
    
    cursor.execute(
        f"UPDATE products SET {set_clause} WHERE id = ?",
        values
    )
    
    conn.commit()
    conn.close()

def delete_product(product_id):
    """Delete product from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    
    conn.commit()
    conn.close()

def create_order(user_uuid, product_id, amount, status="pending"):
    """Create a new order"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Generate a unique transaction ID
    transaction_id = str(uuid_lib.uuid4().hex)[:8].upper()
    
    cursor.execute(
        "INSERT INTO orders (user_uuid, product_id, amount, status, transaction_id) VALUES (?, ?, ?, ?, ?)",
        (user_uuid, product_id, amount, status, transaction_id)
    )
    
    order_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return order_id, transaction_id

def get_order(order_id):
    """Get order from database by ID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.*, p.name as product_name, p.days, p.usage_limit_gb, u.name as user_name
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON o.user_uuid = u.uuid
        WHERE o.id = ?
    """, (order_id,))
    
    order = cursor.fetchone()
    
    conn.close()
    
    if order:
        return dict(order)
    return None

def get_order_by_transaction_id(transaction_id):
    """Get order from database by transaction ID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.*, p.name as product_name, p.days, p.usage_limit_gb, u.name as user_name
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON o.user_uuid = u.uuid
        WHERE o.transaction_id = ?
    """, (transaction_id,))
    
    order = cursor.fetchone()
    
    conn.close()
    
    if order:
        return dict(order)
    return None

def get_user_orders(user_uuid, status=None):
    """Get orders for a user"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if status:
        cursor.execute("""
            SELECT o.*, p.name as product_name, p.days, p.usage_limit_gb
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.user_uuid = ? AND o.status = ?
            ORDER BY o.created_at DESC
        """, (user_uuid, status))
    else:
        cursor.execute("""
            SELECT o.*, p.name as product_name, p.days, p.usage_limit_gb
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.user_uuid = ?
            ORDER BY o.created_at DESC
        """, (user_uuid,))
    
    orders = cursor.fetchall()
    
    conn.close()
    
    return [dict(order) for order in orders]

def get_all_orders(status=None, limit=50, offset=0):
    """Get all orders with pagination"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if status:
        cursor.execute("""
            SELECT o.*, p.name as product_name, u.name as user_name
            FROM orders o
            JOIN products p ON o.product_id = p.id
            JOIN users u ON o.user_uuid = u.uuid
            WHERE o.status = ?
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (status, limit, offset))
    else:
        cursor.execute("""
            SELECT o.*, p.name as product_name, u.name as user_name
            FROM orders o
            JOIN products p ON o.product_id = p.id
            JOIN users u ON o.user_uuid = u.uuid
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    
    orders = cursor.fetchall()
    
    # Get total count
    if status:
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = ?", (status,))
    else:
        cursor.execute("SELECT COUNT(*) FROM orders")
    
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    return [dict(order) for order in orders], total_count

def update_order_status(order_id, status, payment_method=None):
    """Update order status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if payment_method:
        cursor.execute(
            "UPDATE orders SET status = ?, payment_method = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, payment_method, order_id)
        )
    else:
        cursor.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, order_id)
        )
    
    conn.commit()
    conn.close()

def add_payment(order_id, user_uuid, amount, method, status, transaction_id=None, screenshot_file_id=None):
    """Add payment to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO payments 
           (order_id, user_uuid, amount, method, status, transaction_id, screenshot_file_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (order_id, user_uuid, amount, method, status, transaction_id, screenshot_file_id)
    )
    
    payment_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return payment_id

def get_payment(payment_id):
    """Get payment from database by ID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.*, o.transaction_id as order_transaction_id, u.name as user_name
        FROM payments p
        JOIN orders o ON p.order_id = o.id
        JOIN users u ON p.user_uuid = u.uuid
        WHERE p.id = ?
    """, (payment_id,))
    
    payment = cursor.fetchone()
    
    conn.close()
    
    if payment:
        return dict(payment)
    return None

def get_payments_by_order(order_id):
    """Get payments for an order"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM payments WHERE order_id = ? ORDER BY created_at DESC", (order_id,))
    payments = cursor.fetchall()
    
    conn.close()
    
    return [dict(payment) for payment in payments]

def update_payment_status(payment_id, status):
    """Update payment status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE payments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, payment_id)
    )
    
    conn.commit()
    conn.close()

def add_server(title, url, proxy_path, api_key, user_limit=0):
    """Add server to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO servers (title, url, proxy_path, api_key, user_limit) VALUES (?, ?, ?, ?, ?)",
        (title, url, proxy_path, api_key, user_limit)
    )
    
    server_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return server_id

def get_server(server_id):
    """Get server from database by ID"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
    server = cursor.fetchone()
    
    conn.close()
    
    if server:
        return dict(server)
    return None

def get_all_servers(active_only=True):
    """Get all servers"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute("SELECT * FROM servers WHERE is_active = 1")
    else:
        cursor.execute("SELECT * FROM servers")
    
    servers = cursor.fetchall()
    
    conn.close()
    
    return [dict(server) for server in servers]

def update_server(server_id, data):
    """Update server in database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Build SET clause dynamically
    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values())
    values.append(server_id)
    
    cursor.execute(
        f"UPDATE servers SET {set_clause} WHERE id = ?",
        values
    )
    
    conn.commit()
    conn.close()

def delete_server(server_id):
    """Delete server from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    """Get setting from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    return default

def set_setting(key, value):
    """Set setting in database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if setting exists
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    
    if result:
        # Update existing setting
        cursor.execute(
            "UPDATE settings SET value = ? WHERE key = ?",
            (value, key)
        )
    else:
        # Insert new setting
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
    
    conn.commit()
    conn.close()

def add_backup(filename, file_id=None, size=None, backup_type="manual"):
    """Add backup record to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO backups (filename, file_id, size, type) VALUES (?, ?, ?, ?)",
        (filename, file_id, size, backup_type)
    )
    
    backup_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return backup_id

def get_backups(limit=10):
    """Get recent backups"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM backups ORDER BY created_at DESC LIMIT ?", (limit,))
    backups = cursor.fetchall()
    
    conn.close()
    
    return [dict(backup) for backup in backups]

def mark_user_has_free_test(uuid):
    """Mark user as having received free test"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    if user:
        # Update existing user
        cursor.execute(
            "UPDATE users SET has_free_test = 1 WHERE uuid = ?",
            (uuid,)
        )
    else:
        # Get user details from API and add to database
        from Utils.api import get_user, PROXY_PATH, API_KEY
        user_api = get_user(PROXY_PATH, API_KEY, uuid)
        if user_api:
            cursor.execute(
                "INSERT INTO users (uuid, name, has_free_test) VALUES (?, ?, 1)",
                (uuid, user_api["name"])
            )
    
    conn.commit()
    conn.close()

def has_user_free_test(uuid):
    """Check if user has received free test"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT has_free_test FROM users WHERE uuid = ?", (uuid,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0] == 1
    return False

def reset_user_free_test(uuid):
    """Reset user's free test status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    if user:
        # Update existing user
        cursor.execute(
            "UPDATE users SET has_free_test = 0 WHERE uuid = ?",
            (uuid,)
        )
    
    conn.commit()
    conn.close()

def reset_all_free_tests():
    """Reset all users' free test status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET has_free_test = 0")
    
    conn.commit()
    conn.close()

def ban_user(uuid):
    """Ban a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()
    
    if user:
        # Update existing user
        cursor.execute(
            "UPDATE users SET is_banned = 1 WHERE uuid = ?",
            (uuid,)
        )
    else:
        # Get user details from API and add to database
        from Utils.api import get_user, PROXY_PATH, API_KEY
        user_api = get_user(PROXY_PATH, API_KEY, uuid)
        if user_api:
            cursor.execute(
                "INSERT INTO users (uuid, name, is_banned) VALUES (?, ?, 1)",
                (uuid, user_api["name"])
            )
    
    conn.commit()
    conn.close()

def unban_user(uuid):
    """Unban a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET is_banned = 0 WHERE uuid = ?",
        (uuid,)
    )
    
    conn.commit()
    conn.close()

def is_user_banned(uuid):
    """Check if user is banned"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_banned FROM users WHERE uuid = ?", (uuid,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0] == 1
    return False

def get_statistics():
    """Get system statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Total users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # Active users (with telegram_id)
    cursor.execute("SELECT COUNT(*) FROM users WHERE telegram_id IS NOT NULL")
    active_users = cursor.fetchone()[0]
    
    # Total orders
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    
    # Completed orders
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    completed_orders = cursor.fetchone()[0]
    
    # Pending orders
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cursor.fetchone()[0]
    
    # Total revenue
    cursor.execute("SELECT SUM(amount) FROM orders WHERE status = 'completed'")
    result = cursor.fetchone()[0]
    total_revenue = result if result else 0
    
    # Recent orders
    cursor.execute("""
        SELECT o.*, p.name as product_name, u.name as user_name
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON o.user_uuid = u.uuid
        ORDER BY o.created_at DESC
        LIMIT 5
    """)
    recent_orders = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
        "recent_orders": recent_orders
    }


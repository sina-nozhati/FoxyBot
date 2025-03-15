import sys
import os
import telebot
import json
import time
import qrcode
from io import BytesIO
from datetime import datetime, timedelta
import pytz
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.api import *
from Database.dbManager import *

# Load configuration
from config import load_config
config = load_config()

# Extract API parameters
PROXY_PATH, API_KEY = parse_panel_url(config['HIDDIFY_PANEL_URL'])
set_panel_url(config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0])

# Set up Telegram bot
ADMIN_BOT_TOKEN = config['ADMIN_BOT_TOKEN']
ADMIN_TELEGRAM_ID = config['ADMIN_TELEGRAM_ID']
LANGUAGE = config['LANGUAGE']

# Initialize bot
bot = telebot.TeleBot(ADMIN_BOT_TOKEN)

# Load language files
with open(os.path.join(os.path.dirname(__file__), "Json", "messages.json"), "r", encoding="utf-8") as f:
    messages = json.load(f)

with open(os.path.join(os.path.dirname(__file__), "Json", "buttons.json"), "r", encoding="utf-8") as f:
    buttons = json.load(f)

with open(os.path.join(os.path.dirname(__file__), "Json", "commands.json"), "r", encoding="utf-8") as f:
    commands = json.load(f)

# Initialize database
init_db()

# Helper functions
def get_message(key):
    """Get message text in the configured language"""
    return messages[LANGUAGE].get(key, messages["en"].get(key, key))

def get_button(key):
    """Get button text in the configured language"""
    return buttons[LANGUAGE].get(key, buttons["en"].get(key, key))

def get_command(key):
    """Get command in the configured language"""
    return commands[LANGUAGE].get(key, commands["en"].get(key, key))

def is_admin(user_id):
    """Check if user is an admin"""
    return str(user_id) == str(ADMIN_TELEGRAM_ID)

def format_time_ago(last_online):
    """Format last online time as a human-readable string"""
    if not last_online:
        return get_message("NEVER")
    
    try:
        # Parse the datetime string
        if isinstance(last_online, str):
            last_online = datetime.strptime(last_online, "%Y-%m-%d %H:%M:%S")
        
        # Calculate time difference
        now = datetime.now()
        diff = now - last_online
        
        if diff.total_seconds() < 60:
            return get_message("ONLINE")
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} {get_message('MINUTE')} {get_message('AGO')}"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} {get_message('HOUR')} {get_message('AGO')}"
        elif diff.total_seconds() < 604800:
            days = int(diff.total_seconds() / 86400)
            return f"{days} {get_message('DAY')} {get_message('AGO')}"
        elif diff.total_seconds() < 2592000:
            weeks = int(diff.total_seconds() / 604800)
            return f"{weeks} {get_message('WEEK')} {get_message('AGO')}"
        else:
            months = int(diff.total_seconds() / 2592000)
            return f"{months} {get_message('MONTH')} {get_message('AGO')}"
    except Exception as e:
        print(f"Error formatting time: {e}")
        return str(last_online)

def generate_qr_code(data):
    """Generate QR code from data"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

# Command handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    # Create main menu keyboard
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton(get_button("USERS_MANAGEMENT")),
        telebot.types.KeyboardButton(get_button("ORDERS_MANAGEMENT")),
        telebot.types.KeyboardButton(get_button("PAYMENTS_MANAGEMENT")),
        telebot.types.KeyboardButton(get_button("USERS_MANAGEMENT")),
        telebot.types.KeyboardButton(get_button("SERVER_STATUS")),
        telebot.types.KeyboardButton(get_button("BACKUP")),
        telebot.types.KeyboardButton(get_button("SETTINGS"))
    )
    
    bot.send_message(user_id, get_message("WELCOME"), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == get_button("USERS_MANAGEMENT"))
def bot_users_management(message):
    """Handle Bot Users Management button"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        telebot.types.KeyboardButton(get_button("LIST_USERS")),
        telebot.types.KeyboardButton(get_button("SEARCH_USER")),
        telebot.types.KeyboardButton(get_button("ADD_USER")),
        telebot.types.KeyboardButton(get_button("BACK"))
    )
    
    bot.send_message(user_id, get_message("USERS_MANAGEMENT_MENU"), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == get_button("ADD_USER"))
def add_user_command(message):
    """Handle Add User button"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    # Ask for user name
    msg = bot.send_message(user_id, get_message("ADD_USER_NAME"))
    
    # Register next step handler
    bot.register_next_step_handler(msg, process_add_user_name)

def process_add_user_name(message):
    """Process add user name input"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    name = message.text.strip()
    
    if name == "/cancel":
        bot.reply_to(message, get_message("CANCEL_ADD_USER"))
        return
    
    # Store name in user state
    user_state = {"name": name}
    
    # Ask for usage limit
    msg = bot.send_message(user_id, f"📊 {get_message('ADD_USER_USAGE_LIMIT')}\n⚠️ مثال: 30")
    
    # Register next step handler
    bot.register_next_step_handler(msg, process_add_user_usage, user_state)

def process_add_user_usage(message, user_state):
    """Process add user usage input"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    usage = message.text.strip()
    
    if usage == "/cancel":
        bot.reply_to(message, get_message("CANCEL_ADD_USER"))
        return
    
    try:
        # Convert to float
        usage = float(usage)
        
        # Store usage in user state
        user_state["usage_limit_GB"] = usage
        
        # Ask for days
        msg = bot.send_message(user_id, f"⏳ {get_message('ADD_USER_DAYS')}\n⚠️ مثال: 30")
        
        # Register next step handler
        bot.register_next_step_handler(msg, process_add_user_days, user_state)
        
    except ValueError:
        bot.reply_to(message, get_message("ERROR_INVALID_NUMBER"))
        # Ask again
        msg = bot.send_message(user_id, f"📊 {get_message('ADD_USER_USAGE_LIMIT')}\n⚠️ مثال: 30")
        bot.register_next_step_handler(msg, process_add_user_usage, user_state)

def process_add_user_days(message, user_state):
    """Process add user days input"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    days = message.text.strip()
    
    if days == "/cancel":
        bot.reply_to(message, get_message("CANCEL_ADD_USER"))
        return
    
    try:
        # Convert to int
        days = int(days)
        
        # Store days in user state
        user_state["package_days"] = days
        
        # Auto-generate comment with user number
        user_number = random.randint(1000, 9999)
        user_state["comment"] = f"User #{user_number}"
        
        # Set start date to today
        user_state["start_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Show confirmation
        confirm_text = f"🔰 {get_message('ADD_USER_CONFIRM')}\n\n"
        confirm_text += f"👤 {get_message('INFO_USER_NAME')}: {user_state['name']}\n"
        confirm_text += f"📊 {get_message('INFO_USAGE')}: {user_state['usage_limit_GB']} {get_message('GB')}\n"
        confirm_text += f"⏳ {get_message('INFO_REMAINING_DAYS')}: {user_state['package_days']} {get_message('DAY_EXPIRE')}\n"
        confirm_text += f"📝 {get_message('INFO_COMMENT')}: {user_state['comment']}\n"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton(
                get_button("CONFIRM"), callback_data="confirm_add_user"
            ),
            telebot.types.InlineKeyboardButton(
                get_button("CANCEL"), callback_data="cancel_add_user"
            )
        )
        
        msg = bot.send_message(user_id, confirm_text, reply_markup=markup)
        
        # Store message ID and user state for callback
        add_user_states[user_id] = {
            "message_id": msg.message_id,
            "user_state": user_state
        }
        
    except ValueError:
        bot.reply_to(message, get_message("ERROR_INVALID_NUMBER"))
        # Ask again
        msg = bot.send_message(user_id, f"⏳ {get_message('ADD_USER_DAYS')}\n⚠️ مثال: 30")
        bot.register_next_step_handler(msg, process_add_user_days, user_state)

# Store user states for add user process
add_user_states = {}

@bot.callback_query_handler(func=lambda call: call.data == "confirm_add_user")
def handle_confirm_add_user(call):
    """Handle confirm add user callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    if user_id not in add_user_states:
        bot.answer_callback_query(call.id, get_message("ERROR_UNKNOWN"))
        return
    
    user_state = add_user_states[user_id]["user_state"]
    
    try:
        # Add user
        new_user = add_user(PROXY_PATH, API_KEY, user_state)
        
        # Send success message
        bot.edit_message_text(
            f"{get_message('SUCCESS_ADD_USER')}\n\n"
            f"{get_message('NEW_USER_INFO')}\n"
            f"{get_message('INFO_USER_NAME')} {new_user['name']}\n"
            f"{get_message('INFO_USAGE')} {new_user['usage_limit_GB']} {get_message('GB')}\n"
            f"{get_message('INFO_REMAINING_DAYS')} {new_user['package_days']} {get_message('DAY_EXPIRE')}\n"
            f"{get_message('INFO_COMMENT')} {new_user.get('comment', '')}\n"
            f"UUID: {new_user['uuid']}",
            user_id,
            add_user_states[user_id]["message_id"]
        )
        
        # Clean up user state
        del add_user_states[user_id]
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_add_user")
def handle_cancel_add_user(call):
    """Handle cancel add user callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    if user_id in add_user_states:
        # Clean up user state
        del add_user_states[user_id]
    
    # Send cancel message
    bot.edit_message_text(
        get_message("CANCEL_ADD_USER"),
        user_id,
        call.message.message_id
    )
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == get_button("SEARCH_USER"))
def search_users_command(message):
    """Handle Search Users button"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    # Create search methods keyboard
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton(
            get_button("SEARCH_USER_NAME"), callback_data="search_name"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("SEARCH_USER_TELEGRAM_ID"), callback_data="search_telegram_id"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("SEARCH_USER_UUID"), callback_data="search_uuid"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("SEARCH_USER_CONFIG"), callback_data="search_config"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("SEARCH_EXPIRED_USERS"), callback_data="search_expired"
        )
    )
    
    bot.send_message(
        user_id,
        get_message("SEARCH_USER"),
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
def handle_search_method_callback(call):
    """Handle search method selection callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    search_method = call.data.split("_")[1]
    
    if search_method == "expired":
        # Handle expired users search directly
        handle_search_expired_users(call)
        return
    
    # Ask for search query based on method
    if search_method == "name":
        msg = bot.send_message(user_id, get_message("SEARCH_USER_NAME"))
    elif search_method == "telegram_id":
        msg = bot.send_message(user_id, get_message("SEARCH_USER_TELEGRAM_ID"))
    elif search_method == "uuid":
        msg = bot.send_message(user_id, get_message("SEARCH_USER_UUID"))
    elif search_method == "config":
        msg = bot.send_message(user_id, get_message("SEARCH_USER_CONFIG"))
    else:
        bot.answer_callback_query(call.id, get_message("ERROR_INVALID_COMMAND"))
        return
    
    # Register next step handler
    bot.register_next_step_handler(msg, process_search_query, search_method)
    bot.answer_callback_query(call.id)

def process_search_query(message, search_method):
    """Process search query input"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    query = message.text.strip()
    
    if query == "/cancel":
        bot.reply_to(message, get_message("CANCELED"))
        return
    
    # Send waiting message
    wait_msg = bot.send_message(user_id, get_message("WAIT"))
    
    try:
        # Get all users
        users = get_users(PROXY_PATH, API_KEY)
        
        if not users:
            bot.edit_message_text(get_message("ERROR_USER_NOT_FOUND"), user_id, wait_msg.message_id)
            return
        
        # Filter users based on search method and query
        results = []
        if search_method == "name":
            results = [u for u in users if query.lower() in u.get("name", "").lower()]
        elif search_method == "telegram_id":
            results = [u for u in users if u.get("telegram_id") and str(u["telegram_id"]) == query]
        elif search_method == "uuid":
            results = [u for u in users if query.lower() in u.get("uuid", "").lower()]
        elif search_method == "config":
            # This is more complex - need to check configs for each user
            for user in users:
                try:
                    configs = get_user_configs(PROXY_PATH, API_KEY, user["uuid"])
                    for config in configs:
                        if query.lower() in config.get("link", "").lower():
                            results.append(user)
                            break
                except:
                    pass
        
        if not results:
            bot.edit_message_text(get_message("ERROR_USER_NOT_FOUND"), user_id, wait_msg.message_id)
            return
        
        # Show search results
        bot.edit_message_text(
            f"{get_message('SEARCH_RESULT')}\n{get_message('NUM_USERS')} {len(results)}",
            user_id,
            wait_msg.message_id
        )
        
        # Create results keyboard
        for user in results:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                get_button("EDIT_USER"), callback_data=f"user_{user['uuid']}"
            ))
            
            # Format user info
            usage_gb = user.get("current_usage_GB", 0) or 0
            limit_gb = user.get("usage_limit_GB", 0) or 0
            
            info = f"{get_message('INFO_USER_NAME')} {user['name']}\n"
            if user.get("telegram_id"):
                info += f"{get_message('INFO_USER_NUM_ID')} {user['telegram_id']}\n"
            
            info += f"{get_message('INFO_USAGE')} {usage_gb:.2f} {get_message('GB')} {get_message('OF')} {limit_gb:.2f} {get_message('GB')}\n"
            
            # Calculate remaining days
            if user.get("package_days") and user.get("start_date"):
                try:
                    start_date = datetime.strptime(user["start_date"], "%Y-%m-%d").date()
                    today = datetime.now().date()
                    elapsed_days = (today - start_date).days
                    remaining_days = max(0, user["package_days"] - elapsed_days)
                    info += f"{get_message('INFO_REMAINING_DAYS')} {remaining_days} {get_message('DAY_EXPIRE')}\n"
                except Exception as e:
                    print(f"Error calculating days: {e}")
            
            # Last connection
            if user.get("last_online"):
                info += f"{get_message('INFO_LAST_CONNECTION')} {format_time_ago(user['last_online'])}\n"
            
            # Comment
            if user.get("comment"):
                info += f"{get_message('INFO_COMMENT')} {user['comment']}\n"
            
            bot.send_message(user_id, info, reply_markup=markup)
        
    except Exception as e:
        bot.edit_message_text(f"{get_message('ERROR_UNKNOWN')}: {str(e)}", user_id, wait_msg.message_id)

def handle_search_expired_users(call):
    """Handle search for expired users"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    # Send waiting message
    wait_msg = bot.send_message(user_id, get_message("WAIT"))
    
    try:
        # Get all users
        users = get_users(PROXY_PATH, API_KEY)
        
        if not users:
            bot.edit_message_text(get_message("ERROR_USER_NOT_FOUND"), user_id, wait_msg.message_id)
            bot.answer_callback_query(call.id)
            return
        
        # Filter expired users
        today = datetime.now().date()
        expired_users = []
        
        for user in users:
            if user.get("package_days") and user.get("start_date"):
                try:
                    start_date = datetime.strptime(user["start_date"], "%Y-%m-%d").date()
                    elapsed_days = (today - start_date).days
                    if elapsed_days >= user["package_days"]:
                        expired_users.append(user)
                except:
                    pass
        
        if not expired_users:
            bot.edit_message_text(get_message("ERROR_USER_NOT_FOUND"), user_id, wait_msg.message_id)
            bot.answer_callback_query(call.id)
            return
        
        # Show expired users
        bot.edit_message_text(
            f"{get_message('EXPIRED_USERS_LIST')}\n{get_message('NUM_USERS')} {len(expired_users)}",
            user_id,
            wait_msg.message_id
        )
        
        # Create results keyboard
        for user in expired_users:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                get_button("EDIT_USER"), callback_data=f"user_{user['uuid']}"
            ))
            
            # Format user info
            usage_gb = user.get("current_usage_GB", 0) or 0
            limit_gb = user.get("usage_limit_GB", 0) or 0
            
            info = f"{get_message('INFO_USER_NAME')} {user['name']}\n"
            if user.get("telegram_id"):
                info += f"{get_message('INFO_USER_NUM_ID')} {user['telegram_id']}\n"
            
            info += f"{get_message('INFO_USAGE')} {usage_gb:.2f} {get_message('GB')} {get_message('OF')} {limit_gb:.2f} {get_message('GB')}\n"
            info += f"{get_message('INFO_REMAINING_DAYS')} 0 {get_message('DAY_EXPIRE')} ({get_message('USER_TIME_EXPIRED')})\n"
            
            # Last connection
            if user.get("last_online"):
                info += f"{get_message('INFO_LAST_CONNECTION')} {format_time_ago(user['last_online'])}\n"
            
            # Comment
            if user.get("comment"):
                info += f"{get_message('INFO_COMMENT')} {user['comment']}\n"
            
            bot.send_message(user_id, info, reply_markup=markup)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.edit_message_text(f"{get_message('ERROR_UNKNOWN')}: {str(e)}", user_id, wait_msg.message_id)
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == get_button("SERVER_STATUS"))
def server_status_command(message):
    """Handle Server Status button"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    # Send waiting message
    wait_msg = bot.send_message(user_id, get_message("WAIT"))
    
    try:
        # Get server status
        status = get_server_status(PROXY_PATH, API_KEY)
        
        if not status:
            bot.edit_message_text(get_message("ERROR_UNKNOWN"), user_id, wait_msg.message_id)
            return
        
        # Format server status
        stats = status.get("stats", {})
        
        # CPU
        cpu_percent = stats.get("cpu_percent", 0)
        cpu_count = stats.get("cpu_count", 0)
        
        # Memory
        memory = stats.get("memory", {})
        memory_total = memory.get("total", 0) / (1024 * 1024 * 1024)  # Convert to GB
        memory_used = memory.get("used", 0) / (1024 * 1024 * 1024)    # Convert to GB
        memory_percent = memory.get("percent", 0)
        
        # Disk
        disk = stats.get("disk", {})
        disk_total = disk.get("total", 0) / (1024 * 1024 * 1024)  # Convert to GB
        disk_used = disk.get("used", 0) / (1024 * 1024 * 1024)    # Convert to GB
        disk_percent = disk.get("percent", 0)
        
        # Network
        network = stats.get("net_io", {})
        net_sent = network.get("bytes_sent", 0) / (1024 * 1024 * 1024)  # Convert to GB
        net_recv = network.get("bytes_recv", 0) / (1024 * 1024 * 1024)  # Convert to GB
        
        # Format status message
        status_msg = "📊 Server Status\n\n"
        
        # CPU
        status_msg += "🔄 CPU:\n"
        status_msg += f"  • Usage: {cpu_percent:.1f}%\n"
        status_msg += f"  • Cores: {cpu_count}\n\n"
        
        # Memory
        status_msg += "💾 Memory:\n"
        status_msg += f"  • Usage: {memory_used:.2f} GB / {memory_total:.2f} GB ({memory_percent:.1f}%)\n\n"
        
        # Disk
        status_msg += "💿 Disk:\n"
        status_msg += f"  • Usage: {disk_used:.2f} GB / {disk_total:.2f} GB ({disk_percent:.1f}%)\n\n"
        
        # Network
        status_msg += "🌐 Network:\n"
        status_msg += f"  • Sent: {net_sent:.2f} GB\n"
        status_msg += f"  • Received: {net_recv:.2f} GB\n"
        
        # Send status message
        bot.edit_message_text(status_msg, user_id, wait_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"{get_message('ERROR_UNKNOWN')}: {str(e)}", user_id, wait_msg.message_id)

@bot.message_handler(func=lambda message: message.text == get_button("BACKUP"))
def server_backup_command(message):
    """Handle Server Backup button"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    # Send waiting message
    wait_msg = bot.send_message(user_id, get_message("WAIT"))
    
    try:
        # Get all users
        users = get_users(PROXY_PATH, API_KEY)
        
        if not users:
            bot.edit_message_text(get_message("ERROR_USER_NOT_FOUND"), user_id, wait_msg.message_id)
            return
        
        # Create backup file
        backup_data = {
            "users": users,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "panel_url": config['HIDDIFY_PANEL_URL']
        }
        
        backup_file = f"hiddify_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(backup_file, "w") as f:
            json.dump(backup_data, f, indent=4)
        
        # Send backup file
        with open(backup_file, "rb") as f:
            bot.send_document(user_id, f, caption=f"📥 Hiddify Panel Backup\n{datetime.now().strftime('%Y-%m-%d %H%M%S')}")
        
        # Delete temporary file
        os.remove(backup_file)
        
        # Delete waiting message
        bot.delete_message(user_id, wait_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"{get_message('ERROR_UNKNOWN')}: {str(e)}", user_id, wait_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_wallet_"))
def handle_edit_wallet_callback(call):
    """Handle edit wallet callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    uuid = call.data.split("_")[2]
    
    try:
        # Get user from database
        user_db = get_user_from_db(uuid)
        
        if not user_db:
            # User not in database, create entry
            user_api = get_user(PROXY_PATH, API_KEY, uuid)
            if not user_api:
                bot.answer_callback_query(call.id, get_message("ERROR_USER_NOT_FOUND"))
                return
            
            # Add user to database with 0 wallet balance
            add_user_to_db(uuid, user_api["name"], 0)
            wallet_balance = 0
        else:
            wallet_balance = user_db["wallet_balance"]
        
        # Ask for new wallet balance
        msg = bot.send_message(
            user_id,
            f"{get_message('EDIT_WALLET_BALANCE')}\n{get_message('CURRENT_VALUE')}: {wallet_balance} {get_message('TOMAN')}"
        )
        
        # Register next step handler
        bot.register_next_step_handler(msg, process_edit_wallet, uuid)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

def process_edit_wallet(message, uuid):
    """Process edit wallet input"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    new_balance = message.text.strip()
    
    if new_balance == "/cancel":
        bot.reply_to(message, get_message("CANCELED"))
        return
    
    try:
        # Convert to int
        new_balance = int(new_balance)
        
        # Update user wallet balance
        update_user_wallet(uuid, new_balance)
        
        # Get user details
        user_api = get_user(PROXY_PATH, API_KEY, uuid)
        
        if not user_api:
            bot.reply_to(message, get_message("ERROR_USER_NOT_FOUND"))
            return
        
        # Send success message
        bot.reply_to(message, f"{get_message('WALLET_BALANCE_CHANGED_BY_ADMIN_P1')} {new_balance} {get_message('TOMAN')} {get_message('WALLET_BALANCE_CHANGED_BY_ADMIN_P2')}")
        
        # Notify user if they have telegram_id
        if user_api.get("telegram_id"):
            try:
                # Send notification to user
                client_bot_token = config['CLIENT_BOT_TOKEN']
                if client_bot_token:
                    client_bot = telebot.TeleBot(client_bot_token)
                    client_bot.send_message(
                        user_api["telegram_id"],
                        f"{get_message('WALLET_BALANCE_CHANGED_BY_ADMIN_P1')} {new_balance} {get_message('TOMAN')} {get_message('WALLET_BALANCE_CHANGED_BY_ADMIN_P2')}"
                    )
            except Exception as e:
                print(f"Error notifying user: {e}")
        
    except ValueError:
        bot.reply_to(message, get_message("ERROR_INVALID_NUMBER"))
    except Exception as e:
        bot.reply_to(message, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_message_"))
def handle_send_message_callback(call):
    """Handle send message to user callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    uuid = call.data.split("_")[2]
    
    try:
        # Get user details
        user = get_user(PROXY_PATH, API_KEY, uuid)
        
        if not user:
            bot.answer_callback_query(call.id, get_message("ERROR_USER_NOT_FOUND"))
            return
        
        if not user.get("telegram_id"):
            bot.answer_callback_query(call.id, "User doesn't have Telegram ID")
            return
        
        # Ask for message
        msg = bot.send_message(
            user_id,
            f"{get_message('SEND_MESSAGE_TO_USER')}\n{get_message('INFO_USER_NAME')} {user['name']}"
        )
        
        # Register next step handler
        bot.register_next_step_handler(msg, process_send_message, uuid)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

def process_send_message(message, uuid):
    """Process send message input"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    msg_text = message.text.strip()
    
    if msg_text == "/cancel":
        bot.reply_to(message, get_message("CANCELED"))
        return
    
    try:
        # Get user details
        user = get_user(PROXY_PATH, API_KEY, uuid)
        
        if not user:
            bot.reply_to(message, get_message("ERROR_USER_NOT_FOUND"))
            return
        
        if not user.get("telegram_id"):
            bot.reply_to(message, "User doesn't have Telegram ID")
            return
        
        # Send message to user
        client_bot_token = config['CLIENT_BOT_TOKEN']
        if not client_bot_token:
            bot.reply_to(message, get_message("ERROR_CLIENT_TOKEN"))
            return
        
        client_bot = telebot.TeleBot(client_bot_token)
        
        # Format message
        formatted_msg = f"{get_message('MESSAGE_FROM_ADMIN')}\n\n"
        formatted_msg += f"{get_message('ADMIN')} {message.from_user.first_name}\n"
        formatted_msg += f"{get_message('MESSAGE_TEXT')} {msg_text}"
        
        # Send message
        client_bot.send_message(user["telegram_id"], formatted_msg)
        
        # Send success message
        bot.reply_to(message, get_message("MESSAGE_SENDED"))
        
    except Exception as e:
        bot.reply_to(message, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reset_test_"))
def handle_reset_test_callback(call):
    """Handle reset test subscription callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    uuid = call.data.split("_")[2]
    
    try:
        # Get user details
        user = get_user(PROXY_PATH, API_KEY, uuid)
        
        if not user:
            bot.answer_callback_query(call.id, get_message("ERROR_USER_NOT_FOUND"))
            return
        
        # Reset user's free test status in database
        reset_user_free_test(uuid)
        
        # Send success message
        bot.answer_callback_query(call.id, get_message("SUCCESS_RESET_TEST_SUB"))
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ban_user_"))
def handle_ban_user_callback(call):
    """Handle ban user callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    uuid = call.data.split("_")[2]
    
    try:
        # Get user details
        user = get_user(PROXY_PATH, API_KEY, uuid)
        
        if not user:
            bot.answer_callback_query(call.id, get_message("ERROR_USER_NOT_FOUND"))
            return
        
        # Check if user is already banned
        user_db = get_user_from_db(uuid)
        is_banned = user_db and user_db.get("is_banned", 0) == 1
        
        # Create confirmation keyboard
        markup = telebot.types.InlineKeyboardMarkup()
        if is_banned:
            markup.row(
                telebot.types.InlineKeyboardButton(
                    get_button("YES"), callback_data=f"confirm_unban_{uuid}"
                ),
                telebot.types.InlineKeyboardButton(
                    get_button("NO"), callback_data=f"user_{uuid}"
                )
            )
            bot.send_message(
                user_id,
                f"Unban user {user['name']}?",
                reply_markup=markup
            )
        else:
            markup.row(
                telebot.types.InlineKeyboardButton(
                    get_button("YES"), callback_data=f"confirm_ban_{uuid}"
                ),
                telebot.types.InlineKeyboardButton(
                    get_button("NO"), callback_data=f"user_{uuid}"
                )
            )
            bot.send_message(
                user_id,
                f"Ban user {user['name']}?",
                reply_markup=markup
            )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_ban_"))
def handle_confirm_ban_callback(call):
    """Handle confirm ban callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    uuid = call.data.split("_")[2]
    
    try:
        # Ban user
        ban_user(uuid)
        
        # Send success message
        bot.edit_message_text(
            get_message("SUCCESS_BAN_USER"),
            user_id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_unban_"))
def handle_confirm_unban_callback(call):
    """Handle confirm unban callback"""
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, get_message("ERROR_NOT_ADMIN"))
        return
    
    uuid = call.data.split("_")[2]
    
    try:
        # Unban user
        unban_user(uuid)
        
        # Send success message
        bot.edit_message_text(
            get_message("SUCCESS_UNBAN_USER"),
            user_id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('ERROR_UNKNOWN')}: {str(e)}")

@bot.message_handler(func=lambda message: message.text == get_button("BACK"))
def handle_back_button(message):
    """Handle back button press to return to main menu"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, get_message("ERROR_NOT_ADMIN"))
        return
    
    # Return to main menu
    start_command(message)

# Run the bot
if __name__ == "__main__":
    print(f"Starting Admin Bot with language: {LANGUAGE}")
    bot.send_message(ADMIN_TELEGRAM_ID, get_message("WELCOME_TO_ADMIN"))
    bot.polling(none_stop=True)


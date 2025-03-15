import sys
import os
import telebot
import json
import time
import qrcode
import pyperclip
from io import BytesIO
from datetime import datetime, timedelta
import pytz
import uuid as uuid_lib

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.api import *
from Database.dbManager import *
from UserBot.markups import *

# Load configuration
from config import load_config
config = load_config()

# Extract API parameters
PROXY_PATH, API_KEY = parse_panel_url(config['HIDDIFY_PANEL_URL'])
set_panel_url(config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0])

# Set up Telegram bot
CLIENT_BOT_TOKEN = config['CLIENT_BOT_TOKEN']
LANGUAGE = config['LANGUAGE']

# Initialize bot
bot = telebot.TeleBot(CLIENT_BOT_TOKEN)

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
def get_message(key, language=LANGUAGE):
    """Get message text in the configured language"""
    return messages[language].get(key, messages["en"].get(key, key))

def get_button(key):
    """Get button text in the configured language"""
    return buttons[LANGUAGE].get(key, buttons["EN"].get(key, get_message(key)))

def get_command(key):
    """Get command in the configured language"""
    return commands[LANGUAGE].get(key, commands["EN"].get(key, key))

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

def format_message(key, language=LANGUAGE, **kwargs):
    """Format message with placeholders"""
    message = get_message(key, language)
    return message.format(**kwargs)

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

def check_force_join():
    """Check if force join is enabled"""
    return get_setting("force_join", "0") == "1"

def get_channel_id():
    """Get channel ID from settings"""
    return get_setting("channel_id", "")

def check_user_joined_channel(user_id, channel_id):
    """Check if user has joined the channel"""
    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

def check_user_banned(user_id):
    """Check if user is banned"""
    # First check if user has a subscription
    user_sub = get_user_subscription(user_id)
    if not user_sub:
        return False
    
    # Then check if user is banned
    return is_user_banned(user_sub["uuid"])

def get_order_status_text(status, language=LANGUAGE):
    """Get human-readable order status"""
    status_map = {
        "pending": get_message("ORDER_STATUS_PENDING", language),
        "processing": get_message("ORDER_STATUS_PROCESSING", language),
        "completed": get_message("ORDER_STATUS_COMPLETED", language),
        "cancelled": get_message("ORDER_STATUS_CANCELLED", language)
    }
    return status_map.get(status, status)

def format_datetime(dt_str, language=LANGUAGE):
    """Format datetime string for display"""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        if language == "fa":
            # Simple formatting for Persian (would need proper library for real Persian dates)
            return dt.strftime("%Y/%m/%d %H:%M:%S")
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

# Command handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER", LANGUAGE))
        return
    
    # Check force join
    if check_force_join():
        channel_id = get_channel_id()
        if channel_id and not check_user_joined_channel(user_id, channel_id):
            # Create join channel button
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("JOIN_CHANNEL"),
                    url=f"https://t.me/{channel_id.replace('@', '')}"
                )
            )
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("FORCE_JOIN_CHANNEL_ACCEPTED"),
                    callback_data="check_join"
                )
            )
            
            bot.send_message(
                user_id,
                get_message("REQUEST_JOIN_CHANNEL", LANGUAGE),
                reply_markup=markup
            )
            return
    
    # Create main menu
    markup = generate_main_menu(LANGUAGE)
    
    # Send welcome message
    welcome_msg = get_setting("welcome_message", get_message("WELCOME", LANGUAGE))
    bot.send_message(user_id, welcome_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    """Handle check join callback"""
    user_id = call.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.answer_callback_query(call.id, get_message("BANNED_USER", LANGUAGE))
        return
    
    channel_id = get_channel_id()
    if not channel_id:
        # Channel ID not set, proceed
        bot.answer_callback_query(call.id)
        start_command(call.message)
        return
    
    if check_user_joined_channel(user_id, channel_id):
        # User joined, proceed
        bot.answer_callback_query(call.id, get_message("JOIN_CHANNEL_SUCCESSFUL", LANGUAGE))
        bot.delete_message(user_id, call.message.message_id)
        start_command(call.message)
    else:
        # User didn't join
        bot.answer_callback_query(call.id, get_message("REQUEST_JOIN_CHANNEL", LANGUAGE), show_alert=True)

@bot.message_handler(func=lambda message: message.text == get_button("SUBSCRIPTION_STATUS"))
def subscription_status_command(message):
    """Handle Subscription Status button"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER"))
        return
    
    # Check force join
    if check_force_join():
        channel_id = get_channel_id()
        if channel_id and not check_user_joined_channel(user_id, channel_id):
            # Create join channel button
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("JOIN_CHANNEL"),
                    url=f"https://t.me/{channel_id.replace('@', '')}"
                )
            )
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("FORCE_JOIN_CHANNEL_ACCEPTED"),
                    callback_data="check_join"
                )
            )
            
            bot.reply_to(
                message,
                get_message("REQUEST_JOIN_CHANNEL"),
                reply_markup=markup
            )
            return
    
    # Get user subscription
    user_sub = get_user_subscription(user_id)
    
    if not user_sub:
        bot.reply_to(message, get_message("NO_SUBSCRIPTION"))
        return
    
    # Send waiting message
    wait_msg = bot.send_message(user_id, get_message("WAIT"))
    
    try:
        # Get user details from API
        user = get_user(PROXY_PATH, API_KEY, user_sub["uuid"])
        
        if not user:
            bot.edit_message_text(get_message("ERROR_USER_NOT_FOUND"), user_id, wait_msg.message_id)
            return
        
        # Format user info
        usage_gb = user.get("current_usage_GB", 0) or 0
        limit_gb = user.get("usage_limit_GB", 0) or 0
        
        # Check if hyperlink is enabled
        show_hyperlink = get_setting("show_hyperlink", "0") == "1"
        
        if show_hyperlink:
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            user_url = f"{base_url}/{PROXY_PATH}/{user['uuid']}"
            info = f"<a href='{user_url}'>{get_message('INFO_USER')}</a>\n\n"
        else:
            info = f"{get_message('INFO_USER')}\n\n"
        
        # Status
        if user.get("enable", True) and user.get("is_active", True):
            info += f"{get_message('SUBSCRIPTION_STATUS')} {get_message('ACTIVE_SUBSCRIPTION_STATUS')}\n"
        else:
            info += f"{get_message('SUBSCRIPTION_STATUS')} {get_message('DEACTIVE_SUBSCRIPTION_STATUS')}\n"
        
        # Server
        server = get_user_server(user_id)
        if server:
            info += f"{get_message('SERVER')} {server['title']}\n"
        
        # Usage
        info += f"{get_message('INFO_USAGE')} {usage_gb:.2f} {get_message('GB')} {get_message('OF')} {limit_gb:.2f} {get_message('GB')}\n"
        
        # Calculate remaining days
        if user.get("package_days") and user.get("start_date"):
            try:
                start_date = datetime.strptime(user["start_date"], "%Y-%m-%d").date()
                today = datetime.now().date()
                elapsed_days = (today - start_date).days
                remaining_days = max(0, user["package_days"] - elapsed_days)
                
                if remaining_days == 0:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {get_message('USER_TIME_EXPIRED')}\n"
                elif remaining_days == 1:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {get_message('USER_LAST_DAY')}\n"
                else:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {remaining_days} {get_message('DAY_EXPIRE')}\n"
            except Exception as e:
                print(f"Error calculating days: {e}")
        
        # UUID
        info += f"{get_message('INFO_ID')} {user['uuid']}\n"
        
        # Create update button
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            get_button("UPDATE_SUBSCRIPTION_INFO"),
            callback_data="update_subscription_info"
        ))
        
        # Send subscription info
        bot.edit_message_text(info, user_id, wait_msg.message_id, parse_mode="HTML", reply_markup=markup)
        
    except Exception as e:
        bot.edit_message_text(f"{get_message('UNKNOWN_ERROR')}: {str(e)}", user_id, wait_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "update_subscription_info")
def update_subscription_info_callback(call):
    """Handle update subscription info callback"""
    user_id = call.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.answer_callback_query(call.id, get_message("BANNED_USER"))
        return
    
    # Get user subscription
    user_sub = get_user_subscription(user_id)
    
    if not user_sub:
        bot.answer_callback_query(call.id, get_message("NO_SUBSCRIPTION"))
        return
    
    try:
        # Update user usage
        update_user_usage(PROXY_PATH, API_KEY)
        
        # Get updated user details
        user = get_user(PROXY_PATH, API_KEY, user_sub["uuid"])
        
        if not user:
            bot.answer_callback_query(call.id, get_message("ERROR_USER_NOT_FOUND"))
            return
        
        # Format user info
        usage_gb = user.get("current_usage_GB", 0) or 0
        limit_gb = user.get("usage_limit_GB", 0) or 0
        
        # Check if hyperlink is enabled
        show_hyperlink = get_setting("show_hyperlink", "0") == "1"
        
        if show_hyperlink:
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            user_url = f"{base_url}/{PROXY_PATH}/{user['uuid']}"
            info = f"<a href='{user_url}'>{get_message('INFO_USER')}</a>\n\n"
        else:
            info = f"{get_message('INFO_USER')}\n\n"
        
        # Status
        if user.get("enable", True) and user.get("is_active", True):
            info += f"{get_message('SUBSCRIPTION_STATUS')} {get_message('ACTIVE_SUBSCRIPTION_STATUS')}\n"
        else:
            info += f"{get_message('SUBSCRIPTION_STATUS')} {get_message('DEACTIVE_SUBSCRIPTION_STATUS')}\n"
        
        # Server
        server = get_user_server(user_id)
        if server:
            info += f"{get_message('SERVER')} {server['title']}\n"
        
        # Usage
        info += f"{get_message('INFO_USAGE')} {usage_gb:.2f} {get_message('GB')} {get_message('OF')} {limit_gb:.2f} {get_message('GB')}\n"
        
        # Calculate remaining days
        if user.get("package_days") and user.get("start_date"):
            try:
                start_date = datetime.strptime(user["start_date"], "%Y-%m-%d").date()
                today = datetime.now().date()
                elapsed_days = (today - start_date).days
                remaining_days = max(0, user["package_days"] - elapsed_days)
                
                if remaining_days == 0:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {get_message('USER_TIME_EXPIRED')}\n"
                elif remaining_days == 1:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {get_message('USER_LAST_DAY')}\n"
                else:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {remaining_days} {get_message('DAY_EXPIRE')}\n"
            except Exception as e:
                print(f"Error calculating days: {e}")
        
        # UUID
        info += f"{get_message('INFO_ID')} {user['uuid']}\n"
        
        # Create update button
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            get_button("UPDATE_SUBSCRIPTION_INFO"),
            callback_data="update_subscription_info"
        ))
        
        # Update subscription info
        bot.edit_message_text(info, user_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('UNKNOWN_ERROR')}: {str(e)}")

@bot.message_handler(func=lambda message: message.text == get_button("CONFIGS_LIST"))
def configs_list_command(message):
    """Handle Configs List button"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER"))
        return
    
    # Check force join
    if check_force_join():
        channel_id = get_channel_id()
        if channel_id and not check_user_joined_channel(user_id, channel_id):
            # Create join channel button
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("JOIN_CHANNEL"),
                    url=f"https://t.me/{channel_id.replace('@', '')}"
                )
            )
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("FORCE_JOIN_CHANNEL_ACCEPTED"),
                    callback_data="check_join"
                )
            )
            
            bot.reply_to(
                message,
                get_message("REQUEST_JOIN_CHANNEL"),
                reply_markup=markup
            )
            return
    
    # Get user subscription
    user_sub = get_user_subscription(user_id)
    
    if not user_sub:
        bot.reply_to(message, get_message("NO_SUBSCRIPTION"))
        return
    
    # Create configs buttons
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_DIR"), callback_data="config_dir"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_SUB_AUTO"), callback_data="config_sub_auto"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_SUB"), callback_data="config_sub"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_SUB_B64"), callback_data="config_sub_b64"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_CLASH"), callback_data="config_clash"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_HIDDIFY"), callback_data="config_hiddify"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_SING_BOX"), callback_data="config_sing_box"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("CONFIGS_FULL_SING_BOX"), callback_data="config_full_sing_box"
        )
    )
    
    # Send configs menu
    bot.send_message(
        user_id,
        get_message("USER_CONFIGS_LIST"),
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("config_"))
def handle_config_type_callback(call):
    """Handle specific config type callback"""
    user_id = call.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.answer_callback_query(call.id, get_message("BANNED_USER"))
        return
    
    # Get user subscription
    user_sub = get_user_subscription(user_id)
    
    if not user_sub:
        bot.answer_callback_query(call.id, get_message("NO_SUBSCRIPTION"))
        return
    
    config_type = call.data.split("_")[1]
    
    try:
        # Get user configs
        configs = get_user_configs(PROXY_PATH, API_KEY, user_sub["uuid"])
        
        if not configs:
            bot.answer_callback_query(call.id, get_message("ERROR_CONFIG_NOT_FOUND"))
            return
        
        # Find the requested config type
        config = None
        if config_type == "dir":
            # Direct configs - send all as separate messages
            for cfg in configs:
                if cfg.get("type") in ["vmess", "vless", "trojan", "shadowsocks"]:
                    # Send config link
                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(telebot.types.InlineKeyboardButton(
                        get_button("TO_QR"), callback_data=f"qr_{cfg['link']}"
                    ))
                    
                    bot.send_message(
                        user_id,
                        f"{cfg['name']}\n\n{cfg['link']}",
                        reply_markup=markup
                    )
            
            bot.answer_callback_query(call.id)
            return
        elif config_type == "sub_auto":
            # Find subscription link
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            sub_link = f"{base_url}/{PROXY_PATH}/{user_sub['uuid']}/auto"
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                get_button("TO_QR"), callback_data=f"qr_{sub_link}"
            ))
            
            bot.send_message(
                user_id,
                f"Auto Subscription\n\n{sub_link}",
                reply_markup=markup
            )
            
            bot.answer_callback_query(call.id)
            return
        elif config_type == "sub":
            # Find subscription link
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            sub_link = f"{base_url}/{PROXY_PATH}/{user_sub['uuid']}/sub"
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                get_button("TO_QR"), callback_data=f"qr_{sub_link}"
            ))
            
            bot.send_message(
                user_id,
                f"Subscription Link\n\n{sub_link}",
                reply_markup=markup
            )
            
            bot.answer_callback_query(call.id)
            return
        elif config_type == "sub_b64":
            # Find subscription link
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            sub_link = f"{base_url}/{PROXY_PATH}/{user_sub['uuid']}/sub/base64"
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                get_button("TO_QR"), callback_data=f"qr_{sub_link}"
            ))
            
            bot.send_message(
                user_id,
                f"Subscription Link (Base64)\n\n{sub_link}",
                reply_markup=markup
            )
            
            bot.answer_callback_query(call.id)
            return
        elif config_type == "clash":
            # Find clash subscription link
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            sub_link = f"{base_url}/{PROXY_PATH}/{user_sub['uuid']}/clash"
            
            bot.send_message(
                user_id,
                f"Clash Subscription\n\n{sub_link}"
            )
            
            bot.answer_callback_query(call.id)
            return
        elif config_type == "hiddify":
            # Find hiddify subscription link
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            sub_link = f"{base_url}/{PROXY_PATH}/{user_sub['uuid']}/hiddify"
            
            bot.send_message(
                user_id,
                f"Hiddify Subscription\n\n{sub_link}"
            )
            
            bot.answer_callback_query(call.id)
            return
        elif config_type == "sing_box":
            # Find sing-box subscription link
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            sub_link = f"{base_url}/{PROXY_PATH}/{user_sub['uuid']}/singbox"
            
            bot.send_message(
                user_id,
                f"Sing-box Subscription\n\n{sub_link}"
            )
            
            bot.answer_callback_query(call.id)
            return
        elif config_type == "full_sing_box":
            # Find full sing-box subscription link
            base_url = config['HIDDIFY_PANEL_URL'].rstrip("/").rsplit("/", 2)[0]
            sub_link = f"{base_url}/{PROXY_PATH}/{user_sub['uuid']}/singbox/all"
            
            bot.send_message(
                user_id,
                f"Full Sing-box Subscription\n\n{sub_link}"
            )
            
            bot.answer_callback_query(call.id)
            return
        else:
            bot.answer_callback_query(call.id, get_message("ERROR_CONFIG_NOT_FOUND"))
            return
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('UNKNOWN_ERROR')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("qr_"))
def handle_qr_callback(call):
    """Handle QR code generation callback"""
    user_id = call.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.answer_callback_query(call.id, get_message("BANNED_USER"))
        return
    
    data = call.data[3:]  # Remove "qr_" prefix
    
    try:
        # Generate QR code
        qr_img = generate_qr_code(data)
        
        # Send QR code
        bot.send_photo(user_id, qr_img)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('UNKNOWN_ERROR')}: {str(e)}")

@bot.message_handler(func=lambda message: message.text == get_button("LINK_SUBSCRIPTION"))
def link_subscription_command(message):
    """Handle Link Subscription button"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER"))
        return
    
    # Check force join
    if check_force_join():
        channel_id = get_channel_id()
        if channel_id and not check_user_joined_channel(user_id, channel_id):
            # Create join channel button
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("JOIN_CHANNEL"),
                    url=f"https://t.me/{channel_id.replace('@', '')}"
                )
            )
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("FORCE_JOIN_CHANNEL_ACCEPTED"),
                    callback_data="check_join"
                )
            )
            
            bot.reply_to(
                message,
                get_message("REQUEST_JOIN_CHANNEL"),
                reply_markup=markup
            )
            return
    
    # Check if user already has subscription
    user_sub = get_user_subscription(user_id)
    
    if user_sub:
        bot.reply_to(message, get_message("ALREADY_SUBSCRIBED"))
        return
    
    # Ask for subscription info
    msg = bot.send_message(user_id, get_message("ENTER_SUBSCRIPTION_INFO"))
    
    # Register next step handler
    bot.register_next_step_handler(msg, process_link_subscription)

def process_link_subscription(message):
    """Process link subscription input"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER"))
        return
    
    subscription_info = message.text.strip()
    
    if subscription_info == "/cancel":
        bot.reply_to(message, get_message("CANCELED"))
        return
    
    # Send waiting message
    wait_msg = bot.send_message(user_id, get_message("WAIT"))
    
    try:
        # Try to find user by subscription info
        users = get_users(PROXY_PATH, API_KEY)
        
        if not users:
            bot.edit_message_text(get_message("SUBSCRIPTION_INFO_NOT_FOUND"), user_id, wait_msg.message_id)
            return
        
        # Search for user by UUID or config
        found_user = None
        
        # First try direct UUID match
        for user in users:
            if user.get("uuid") and user.get("uuid").lower() == subscription_info.lower():
                found_user = user
                break
        
        # If not found, try to find in configs
        if not found_user:
            for user in users:
                try:
                    configs = get_user_configs(PROXY_PATH, API_KEY, user["uuid"])
                    for config in configs:
                        if subscription_info.lower() in config.get("link", "").lower():
                            found_user = user
                            break
                    if found_user:
                        break
                except:
                    pass
        
        if not found_user:
            bot.edit_message_text(get_message("SUBSCRIPTION_INFO_NOT_FOUND"), user_id, wait_msg.message_id)
            return
        
        # Ask for confirmation
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton(
                get_button("YES"), callback_data=f"confirm_link_{found_user['uuid']}"
            ),
            telebot.types.InlineKeyboardButton(
                get_button("NO"), callback_data="cancel_link"
            )
        )
        
        # Format user info
        usage_gb = found_user.get("current_usage_GB", 0) or 0
        limit_gb = found_user.get("usage_limit_GB", 0) or 0
        
        info = f"{get_message('CONFIRM_SUBSCRIPTION_QUESTION')}\n\n"
        info += f"{get_message('NAME')} {found_user['name']}\n"
        info += f"{get_message('INFO_USAGE')} {usage_gb:.2f} {get_message('GB')} {get_message('OF')} {limit_gb:.2f} {get_message('GB')}\n"
        
        # Calculate remaining days
        if found_user.get("package_days") and found_user.get("start_date"):
            try:
                start_date = datetime.strptime(found_user["start_date"], "%Y-%m-%d").date()
                today = datetime.now().date()
                elapsed_days = (today - start_date).days
                remaining_days = max(0, found_user["package_days"] - elapsed_days)
                
                if remaining_days == 0:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {get_message('USER_TIME_EXPIRED')}\n"
                elif remaining_days == 1:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {get_message('USER_LAST_DAY')}\n"
                else:
                    info += f"{get_message('INFO_REMAINING_DAYS')} {remaining_days} {get_message('DAY_EXPIRE')}\n"
            except Exception as e:
                print(f"Error calculating days: {e}")
        
        bot.edit_message_text(info, user_id, wait_msg.message_id, reply_markup=markup)
        
    except Exception as e:
        bot.edit_message_text(f"{get_message('UNKNOWN_ERROR')}: {str(e)}", user_id, wait_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_link_"))
def handle_confirm_link_callback(call):
    """Handle confirm link subscription callback"""
    user_id = call.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.answer_callback_query(call.id, get_message("BANNED_USER"))
        return
    
    uuid = call.data.split("_")[2]
    
    try:
        # Get user details
        user = get_user(PROXY_PATH, API_KEY, uuid)
        
        if not user:
            bot.answer_callback_query(call.id, get_message("ERROR_USER_NOT_FOUND"))
            return
        
        # Link subscription to user
        link_user_subscription(user_id, uuid, user["name"])
        
        # Update user telegram_id in API
        update_user(PROXY_PATH, API_KEY, uuid, {"telegram_id": user_id})
        
        # Send success message
        bot.edit_message_text(
            get_message("SUBSCRIPTION_CONFIRMED"),
            user_id,
            call.message.message_id
        )
        
        # Update main menu
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            telebot.types.KeyboardButton(get_button("SUBSCRIPTION_STATUS")),
            telebot.types.KeyboardButton(get_button("CONFIGS_LIST")),
            telebot.types.KeyboardButton(get_button("WALLET")),
            telebot.types.KeyboardButton(get_button("RENEWAL_SUBSCRIPTION")),
            telebot.types.KeyboardButton(get_button("MANUAL")),
            telebot.types.KeyboardButton(get_button("SEND_TICKET"))
        )
        
        # Check if FAQ is enabled
        if get_setting("show_faq", "0") == "1":
            markup.add(telebot.types.KeyboardButton(get_button("FAQ")))
        
        bot.send_message(user_id, get_message("WELCOME"), reply_markup=markup)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('UNKNOWN_ERROR')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_link")
def handle_cancel_link_callback(call):
    """Handle cancel link subscription callback"""
    user_id = call.from_user.id
    
    # Send cancel message
    bot.edit_message_text(
        get_message("CANCEL_SUBSCRIPTION"),
        user_id,
        call.message.message_id
    )
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == get_button("UNLINK_SUBSCRIPTION"))
def unlink_subscription_command(message):
    """Handle Unlink Subscription button"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER"))
        return
    
    # Check force join
    if check_force_join():
        channel_id = get_channel_id()
        if channel_id and not check_user_joined_channel(user_id, channel_id):
            # Create join channel button
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("JOIN_CHANNEL"),
                    url=f"https://t.me/{channel_id.replace('@', '')}"
                )
            )
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("FORCE_JOIN_CHANNEL_ACCEPTED"),
                    callback_data="check_join"
                )
            )
            
            bot.reply_to(
                message,
                get_message("REQUEST_JOIN_CHANNEL"),
                reply_markup=markup
            )
            return
    
    # Get user subscription
    user_sub = get_user_subscription(user_id)
    
    if not user_sub:
        bot.reply_to(message, get_message("NO_SUBSCRIPTION"))
        return
    
    # Ask for confirmation
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(
            get_button("YES"), callback_data="confirm_unlink"
        ),
        telebot.types.InlineKeyboardButton(
            get_button("NO"), callback_data="cancel_unlink"
        )
    )
    
    bot.send_message(
        user_id,
        f"{get_message('UNLINK_SUBSCRIPTION')}?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "confirm_unlink")
def handle_confirm_unlink_callback(call):
    """Handle confirm unlink subscription callback"""
    user_id = call.from_user.id
    
    # Get user subscription
    user_sub = get_user_subscription(user_id)
    
    if not user_sub:
        bot.answer_callback_query(call.id, get_message("NO_SUBSCRIPTION"))
        return
    
    try:
        # Unlink subscription
        unlink_user_subscription(user_id)
        
        # Update user telegram_id in API
        update_user(PROXY_PATH, API_KEY, user_sub["uuid"], {"telegram_id": None})
        
        # Send success message
        bot.edit_message_text(
            get_message("SUBSCRIPTION_UNLINKED"),
            user_id,
            call.message.message_id
        )
        
        # Update main menu
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            telebot.types.KeyboardButton(get_button("LINK_SUBSCRIPTION")),
            telebot.types.KeyboardButton(get_button("BUY_SUBSCRIPTION")),
            telebot.types.KeyboardButton(get_button("FREE_TEST")),
            telebot.types.KeyboardButton(get_button("MANUAL")),
            telebot.types.KeyboardButton(get_button("SEND_TICKET"))
        )
        
        # Check if FAQ is enabled
        if get_setting("show_faq", "0") == "1":
            markup.add(telebot.types.KeyboardButton(get_button("FAQ")))
        
        bot.send_message(user_id, get_message("WELCOME"), reply_markup=markup)
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"{get_message('UNKNOWN_ERROR')}: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_unlink")
def handle_cancel_unlink_callback(call):
    """Handle cancel unlink subscription callback"""
    user_id = call.from_user.id
    
    # Send cancel message
    bot.edit_message_text(
        get_message("CANCELED"),
        user_id,
        call.message.message_id
    )
    
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text == get_button("WALLET"))
def wallet_command(message):
    """Handle Wallet button"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER"))
        return
    
    # Check force join
    if check_force_join():
        channel_id = get_channel_id()
        if channel_id and not check_user_joined_channel(user_id, channel_id):
            # Create join channel button
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("JOIN_CHANNEL"),
                    url=f"https://t.me/{channel_id.replace('@', '')}"
                )
            )
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_button("FORCE_JOIN_CHANNEL_ACCEPTED"),
                    callback_data="check_join"
                )
            )
            
            bot.reply_to(
                message,
                get_message("REQUEST_JOIN_CHANNEL"),
                reply_markup=markup
            )
            return
    
    # Get user subscription
    user_sub = get_user_subscription(user_id)
    
    if not user_sub:
        bot.reply_to(message, get_message("NO_SUBSCRIPTION"))
        return
    
    # Get user wallet balance
    user_db = get_user_from_db(user_sub["uuid"])
    
    if not user_db:
        # User not in database, create entry
        add_user_to_db(user_sub["uuid"], user_sub["name"], 0)
        wallet_balance = 0
    else:
        wallet_balance = user_db["wallet_balance"]
    
    # Create wallet menu
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(
        get_button("INCREASE_WALLET_BALANCE"),
        callback_data="increase_wallet_balance"
    ))
    
    if wallet_balance > 0:
        # Show wallet balance
        bot.send_message(
            user_id,
            f"{get_message('WALLET_INFO_PART_1')} {wallet_balance} {get_message('TOMAN')} {get_message('WALLET_INFO_PART_2')}",
            reply_markup=markup
        )
    else:
        # Show zero balance
        bot.send_message(
            user_id,
            get_message("ZERO_BALANCE"),
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == "increase_wallet_balance")
def handle_increase_wallet_balance_callback(call):
    """Handle increase wallet balance callback"""
    user_id = call.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.answer_callback_query(call.id, get_message("BANNED_USER"))
        return
    
    # Get minimum deposit amount
    min_deposit = int(get_setting("min_deposit", "10000"))
    
    # Ask for amount
    msg = bot.send_message(
        user_id,
        f"{get_message('INCREASE_WALLET_BALANCE_AMOUNT')}\n{get_message('MINIMUM_DEPOSIT_AMOUNT')} {min_deposit} {get_message('TOMAN')}"
    )
    
    # Register next step handler
    bot.register_next_step_handler(msg, process_increase_wallet_balance)
    bot.answer_callback_query(call.id)

def process_increase_wallet_balance(message):
    """Process increase wallet balance input"""
    user_id = message.from_user.id
    
    # Check if user is banned
    if check_user_banned(user_id):
        bot.reply_to(message, get_message("BANNED_USER"))
        return
    
    amount = message.text.strip()
    
    if amount == "/cancel":
        bot.reply_to(message, get_message("CANCEL_INCREASE_WALLET_BALANCE"))
        return
    
    try:
        # Convert to int
        amount = int(amount)
        
        # Check minimum deposit
        min_deposit = int(get_setting("min_deposit", "10000"))
        
        if amount < min_deposit:
            bot.reply_to(message, f"{get_message('MINIMUM_DEPOSIT_AMOUNT')} {min_deposit} {get_message('TOMAN')}")
            return
        
        # Get user subscription
        user_sub = get_user_subscription(user_id)
        
        if not user_sub:
            bot.reply_to(message, get_message("NO_SUBSCRIPTION"))
            return
        
        # Create payment methods keyboard
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            get_button("BUY_PLAN"),
            callback_data=f"payment_method_card_{amount}"
        ))
        
        bot.send_message(
            user_id,
            f"{get_message('INCREASE_WALLET_BALANCE_AMOUNT')}: {amount} {get_message
        ))
        
        bot.send_message(
            user_id,
            f"{get_message('INCREASE_WALLET_BALANCE_AMOUNT')}: {amount} {get_message


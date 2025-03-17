import os
import json
import sys
import getpass
import requests
import telebot
from Utils.api import parse_panel_url, set_panel_url, ping_panel

# Default configuration
default_config = {
    "ADMIN_TELEGRAM_ID": "",
    "ADMIN_BOT_TOKEN": "",
    "CLIENT_BOT_TOKEN": "",
    "HIDDIFY_PANEL_URL": "",
    "LANGUAGE": "fa",
    "BACKUP_ENABLED": "1",
    "BACKUP_INTERVAL": "24",  # hours
    "BACKUP_CLOUD_ENABLED": "0",
    "BACKUP_CLOUD_TOKEN": "",
    "PAYMENT_METHODS": json.dumps({
        "card": {
            "enabled": True,
            "card_number": "6037-xxxx-xxxx-xxxx",
            "card_holder": "نام صاحب کارت"
        },
        "crypto": {
            "enabled": False,
            "wallet_address": ""
        }
    })
}

# File paths
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
ADMIN_BOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AdminBot")
USER_BOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserBot")

def validate_telegram_bot(token, bot_type="admin"):
    """Validate Telegram bot token and get bot info"""
    try:
        # Create bot instance
        bot = telebot.TeleBot(token)
        
        # Get bot info
        bot_info = bot.get_me()
        
        if not bot_info:
            print(f"Error: Invalid {bot_type} bot token")
            return False, None
            
        print(f"\n{bot_type.capitalize()} Bot Info:")
        print(f"Bot Username: @{bot_info.username}")
        print(f"Bot Name: {bot_info.first_name}")
        if bot_info.last_name:
            print(f"Bot Last Name: {bot_info.last_name}")
            
        return True, bot_info
        
    except Exception as e:
        print(f"Error validating {bot_type} bot token: {str(e)}")
        return False, None

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return default_config.copy()

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def validate_panel_url(url):
    """Validate Hiddify panel URL format and connectivity"""
    try:
        # Remove trailing slashes
        url = url.rstrip("/")
        
        # Split URL into parts
        parts = url.split("/")
        
        # Check if URL has at least 2 parts (base URL and proxy_path)
        if len(parts) < 4:
            print("Invalid panel URL format. URL should contain base URL, proxy_path and API key.")
            return False
            
        # Get base URL, proxy_path and api_key
        base_url = "/".join(parts[:-2])
        proxy_path = parts[-2]
        api_key = parts[-1]
        
        # Set base URL for API calls
        set_panel_url(base_url)
        
        # Test connection to panel
        try:
            result = ping_panel(proxy_path, api_key)
            if "error" in result:
                print(f"Error connecting to panel: {result['error']}")
                print(f"Please check if the URL is correct: {base_url}/{proxy_path}/api/v2/panel/ping/")
                return False
            print("Successfully connected to panel!")
            return True
        except Exception as e:
            print(f"Error connecting to panel: {str(e)}")
            print(f"Please check if the URL is correct: {base_url}/{proxy_path}/api/v2/panel/ping/")
            return False
            
    except Exception as e:
        print(f"Invalid panel URL: {e}")
        return False

def setup_config():
    """Interactive configuration setup"""
    config = load_config()
    
    print("\n=== FoxyBot Configuration ===\n")
    
    # Admin Telegram ID
    admin_id = input(f"Enter Admin Telegram ID [{config['ADMIN_TELEGRAM_ID']}]: ")
    if admin_id:
        config['ADMIN_TELEGRAM_ID'] = admin_id
    
    # Admin Bot Token
    while True:
        admin_token = input(f"Enter Admin Bot Token [{config['ADMIN_BOT_TOKEN']}]: ")
        if not admin_token and config['ADMIN_BOT_TOKEN']:
            break
            
        if admin_token:
            is_valid, bot_info = validate_telegram_bot(admin_token, "admin")
            if is_valid:
                config['ADMIN_BOT_TOKEN'] = admin_token
                break
            else:
                print("Invalid admin bot token. Please try again.")
        else:
            print("Admin bot token is required.")
    
    # Client Bot Token
    while True:
        client_token = input(f"Enter Client Bot Token [{config['CLIENT_BOT_TOKEN']}]: ")
        if not client_token and config['CLIENT_BOT_TOKEN']:
            break
            
        if client_token:
            is_valid, bot_info = validate_telegram_bot(client_token, "client")
            if is_valid:
                config['CLIENT_BOT_TOKEN'] = client_token
                break
            else:
                print("Invalid client bot token. Please try again.")
        else:
            print("Client bot token is required.")
    
    # Hiddify Panel URL
    while True:
        panel_url = input(f"Enter Hiddify Panel URL [{config['HIDDIFY_PANEL_URL']}]: ")
        if not panel_url and config['HIDDIFY_PANEL_URL']:
            break
        
        if panel_url:
            if validate_panel_url(panel_url):
                config['HIDDIFY_PANEL_URL'] = panel_url
                break
            else:
                print("Invalid panel URL format or unable to connect. Please try again.")
        else:
            print("Panel URL is required.")
    
    # Language
    lang = input(f"Enter Language (en/fa) [{config['LANGUAGE']}]: ")
    if lang and lang in ["en", "fa"]:
        config['LANGUAGE'] = lang
    
    # Backup settings
    backup_enabled = input(f"Enable automatic backup (1/0) [{config['BACKUP_ENABLED']}]: ")
    if backup_enabled in ["0", "1"]:
        config['BACKUP_ENABLED'] = backup_enabled
    
    if config['BACKUP_ENABLED'] == "1":
        backup_interval = input(f"Backup interval in hours [{config['BACKUP_INTERVAL']}]: ")
        if backup_interval.isdigit() and int(backup_interval) > 0:
            config['BACKUP_INTERVAL'] = backup_interval
        
        backup_cloud = input(f"Enable cloud backup (1/0) [{config['BACKUP_CLOUD_ENABLED']}]: ")
        if backup_cloud in ["0", "1"]:
            config['BACKUP_CLOUD_ENABLED'] = backup_cloud
        
        if config['BACKUP_CLOUD_ENABLED'] == "1":
            backup_token = input(f"Enter cloud storage token: ")
            if backup_token:
                config['BACKUP_CLOUD_TOKEN'] = backup_token
    
    # Payment methods
    payment_methods = json.loads(config['PAYMENT_METHODS'])
    
    # Card payment
    card_enabled = input(f"Enable card payment (1/0) [{1 if payment_methods['card']['enabled'] else 0}]: ")
    if card_enabled in ["0", "1"]:
        payment_methods['card']['enabled'] = card_enabled == "1"
    
    if payment_methods['card']['enabled']:
        card_number = input(f"Card number [{payment_methods['card']['card_number']}]: ")
        if card_number:
            payment_methods['card']['card_number'] = card_number
        
        card_holder = input(f"Card holder name [{payment_methods['card']['card_holder']}]: ")
        if card_holder:
            payment_methods['card']['card_holder'] = card_holder
    
    # Crypto payment
    crypto_enabled = input(f"Enable crypto payment (1/0) [{1 if payment_methods['crypto']['enabled'] else 0}]: ")
    if crypto_enabled in ["0", "1"]:
        payment_methods['crypto']['enabled'] = crypto_enabled == "1"
    
    if payment_methods['crypto']['enabled']:
        wallet_address = input(f"Wallet address [{payment_methods['crypto']['wallet_address']}]: ")
        if wallet_address:
            payment_methods['crypto']['wallet_address'] = wallet_address
    
    config['PAYMENT_METHODS'] = json.dumps(payment_methods)
    
    # Save configuration
    save_config(config)
    print("\nConfiguration saved successfully!\n")
    
    # Extract and store proxy_path and api_key
    proxy_path, api_key = parse_panel_url(config['HIDDIFY_PANEL_URL'])
    config['PROXY_PATH'] = proxy_path
    config['API_KEY'] = api_key
    
    return config

if __name__ == "__main__":
    config = setup_config()
    # Export important variables
    ADMIN_TELEGRAM_ID = config['ADMIN_TELEGRAM_ID']
    ADMIN_BOT_TOKEN = config['ADMIN_BOT_TOKEN']
    CLIENT_BOT_TOKEN = config['CLIENT_BOT_TOKEN']
    HIDDIFY_PANEL_URL = config['HIDDIFY_PANEL_URL']
    LANGUAGE = config['LANGUAGE']
    PROXY_PATH = config['PROXY_PATH']
    API_KEY = config['API_KEY']


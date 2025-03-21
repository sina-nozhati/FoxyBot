import os
import json
import sys
import getpass
import requests
import telebot
from termcolor import colored
from Utils.api import parse_panel_url, set_panel_url, ping_panel
from version import __version__
import logging
from urllib.parse import urlparse

# Bypass proxy
os.environ['no_proxy'] = '*'

VERSION = __version__

# File paths
USERS_DB_LOC = os.path.join(os.getcwd(), "Database", "hidyBot.db")
LOG_DIR = os.path.join(os.getcwd(), "Logs")
LOG_LOC = os.path.join(LOG_DIR, "hidyBot.log")
BACKUP_LOC = os.path.join(os.getcwd(), "Backup")
RECEIPTIONS_LOC = os.path.join(os.getcwd(), "UserBot", "Receiptions")
BOT_BACKUP_LOC = os.path.join(os.getcwd(), "Backup", "Bot")
API_PATH = "/api/v2"
HIDY_BOT_ID = "@HidyBotGroup"
PROXY_PATH = None  # Will be set in set_config_variables function

# if directories not exists, create it
if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)
if not os.path.exists(BACKUP_LOC):
    os.mkdir(BACKUP_LOC)
if not os.path.exists(BOT_BACKUP_LOC):
    os.mkdir(BOT_BACKUP_LOC)
if not os.path.exists(RECEIPTIONS_LOC):
    os.mkdir(RECEIPTIONS_LOC)

# set logging  
logging.basicConfig(handlers=[logging.FileHandler(filename=LOG_LOC,
                                                  encoding='utf-8', mode='w')],
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

def setup_users_db():
    try:
        if not os.path.exists(USERS_DB_LOC):
            logging.error(f"Database file not found in {USERS_DB_LOC} directory!")
            with open(USERS_DB_LOC, "w") as f:
                pass
    except Exception as e:
        logging.error(f"Error while connecting to database \n Error:{e}")
        raise Exception(f"Error while connecting to database \nBe in touch with {HIDY_BOT_ID}")

setup_users_db()
from Database.dbManager import UserDBManager

def load_config(db):
    try:
        config = db.select_str_config()
        if not config:
            db.set_default_configs()
            config = db.select_str_config()
        configs = {}
        for conf in config:
            configs[conf['key']] = conf['value']
        return configs
    except Exception as e:
        logging.error(f"Error while loading config \n Error:{e}")
        raise Exception(f"Error while loading config \nBe in touch with {HIDY_BOT_ID}")

def load_server_url(db):
    try:
        panel_url = db.select_servers()
        if not panel_url:
            return None
        
        # Get the URL from database
        url = panel_url[0]['url']
        
        # Ensure URL has scheme
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            # Update in database
            db.edit_server(panel_url[0]['id'], url=url)
            print(colored(f"URL updated with scheme: {url}", "green"))
            
        return url
    except Exception as e:
        logging.error(f"Error while loading panel_url \n Error:{e}")
        raise Exception(f"Error while loading panel_url \nBe in touch with {HIDY_BOT_ID}")

ADMINS_ID, TELEGRAM_TOKEN, CLIENT_TOKEN, PANEL_URL, LANG, PANEL_ADMIN_ID = None, None, None, None, None, None

def set_config_variables(configs, server_url):
    if not configs['bot_admin_id'] and not configs['bot_token_admin'] and not configs['bot_lang'] or not server_url:
        print(colored("Config is not set! , Please run config.py first", "red"))
        raise Exception(f"Config is not set!\nBe in touch with {HIDY_BOT_ID}")

    global ADMINS_ID, TELEGRAM_TOKEN, PANEL_URL, LANG, PANEL_ADMIN_ID, CLIENT_TOKEN, PROXY_PATH
    json_admin_ids = configs["bot_admin_id"]
    ADMINS_ID = json.loads(json_admin_ids)
    TELEGRAM_TOKEN = configs["bot_token_admin"]
    try:
        CLIENT_TOKEN = configs["bot_token_client"]
    except KeyError:
        CLIENT_TOKEN = None

    if CLIENT_TOKEN:
        setup_users_db()
    
    # Set the panel URL
    PANEL_URL = server_url
    LANG = configs["bot_lang"]
    
    # Set base URL for API calls
    parsed_url = urlparse(PANEL_URL)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    set_panel_url(base_url)
    
    # Extract proxy_path and api_key from the panel URL
    try:
        proxy_path, api_key = parse_panel_url(PANEL_URL)
        PANEL_ADMIN_ID = api_key  # Set the admin ID to the API key
        PROXY_PATH = proxy_path  # Set the proxy path
        
        print(colored(f"Successfully parsed panel URL:", "green"))
        print(colored(f"Base URL: {base_url}", "green"))
        print(colored(f"Proxy Path: {proxy_path}", "green"))
        print(colored(f"API Key: {api_key}", "green"))
        print(colored(f"Admin ID: {PANEL_ADMIN_ID}", "green"))
        
        # Test connection to panel
        print(colored("Testing connection to panel...", "cyan"))
        result = ping_panel(proxy_path, api_key)
        if "error" in result:
            print(colored(f"Error connecting to panel: {result['error']}", "red"))
            print(colored(f"Please check if the URL is correct: {base_url}/{proxy_path}/api/v2/panel/ping/", "yellow"))
            return False
        else:
            print(colored("Panel connection successful!", "green"))
        
    except Exception as e:
        print(colored(f"Error parsing panel URL: {str(e)}", "red"))
        raise Exception(f"Error parsing panel URL!\nBe in touch with {HIDY_BOT_ID}")

def panel_url_validator(url):
    """Validate Hiddify panel URL format and connectivity"""
    try:
        # Parse URL to extract proxy_path and api_key
        proxy_path, api_key = parse_panel_url(url)
        
        # Set base URL for API calls
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        set_panel_url(base_url)
        
        # Test connection to panel
        print(colored("Testing connection to panel...", "cyan"))
        result = ping_panel(proxy_path, api_key)
        if "error" in result:
            print(colored(f"Error connecting to panel: {result['error']}", "red"))
            print(colored(f"Please check if the URL is correct: {base_url}/{proxy_path}/api/v2/panel/ping/", "yellow"))
            return False
            
        print(colored("Successfully connected to panel!", "green"))
        return True
    except ValueError as e:
        # This is raised by parse_panel_url if the URL format is invalid
        print(colored(f"Invalid panel URL format: {e}", "red"))
        return False
    except Exception as e:
        print(colored(f"Error validating panel URL: {e}", "red"))
        return False

def bot_token_validator(token):
    print(colored("Checking Bot Token...", "yellow"))
    try:
        request = requests.get(f"https://api.telegram.org/bot{token}/getMe")
    except requests.exceptions.ConnectionError:
        print(colored("Bot Token is not valid! Error in connection", "red"))
        return False
    if request.status_code != 200:
        print(colored("Bot Token is not valid!", "red"))
        return False
    elif request.status_code == 200:
        print(colored("Bot Username:", "green"), "@"+request.json()['result']['username'])
    return True

def set_by_user():
    print()
    print(colored("Example: 123456789\nIf you have more than one admin, split with comma(,)\n[get it from @userinfobot]", "yellow"))
    while True:
        admin_id = input("[+] Enter Telegram Admin Number IDs: ")
        admin_ids = admin_id.split(',')
        admin_ids = [admin_id.strip() for admin_id in admin_ids]
        if not all(admin_id.isdigit() for admin_id in admin_ids):
            print(colored("Admin IDs must be numbers separated by commas!", "red"))
            continue
        admin_ids = [int(admin_id) for admin_id in admin_ids]
        break
            
    print()
    print(colored("Example: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ\n[get it from @BotFather]", "yellow"))
    while True:
        token = input("[+] Enter your Admin bot token: ")
        if not token:
            print(colored("Token is required", "red"))
            continue
        if not bot_token_validator(token):
            continue
        break
    
    print()
    print(colored("You can use the bot as a userbot for your clients!", "yellow"))
    client_token = None  # تعیین مقدار پیش‌فرض
    while True:
        userbot = input("Do you want a Bot for your users? (y/n): ").lower()
        if userbot not in ["y", "n"]:
            print(colored("Please enter y or n!", "red"))
            continue
        break
            
    if userbot == "y":
        print()
        print(colored("Example: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ\n[get it from @BotFather]", "yellow"))
        while True:
            client_token = input("[+] Enter your client (For Users) bot token: ")
            if not client_token:
                print(colored("Token is required!", "red"))
                continue
            if client_token == token:
                print(colored("Client token must be different from Admin token!", "red"))
                continue
            if not bot_token_validator(client_token):
                continue
            # اگر به اینجا رسیدیم، یعنی توکن معتبر است
            break
    
    print()
    print(colored("Example: https://panel.example.com/7frgemkvtE0/78854985-68dp-425c-989b-7ap0c6kr9bd4\n[exactly like this!]", "yellow"))
    panel_url = None
    while True:
        url = input("[+] Enter your panel URL:")
        if not url:
            print(colored("URL is required!", "red"))
            continue
        
        # ذخیره URL اصلی
        panel_url = url
        
        # اعتبارسنجی URL
        if not panel_url_validator(url):
            continue
        
        break

    print()
    print(colored("Example: EN (default: FA)\n[It is better that the language of the bot is the same as the panel]", "yellow"))
    while True:
        lang = input("[+] Select your language (EN(English), FA(Persian)): ") or "FA"
        if lang not in ["EN", "FA"]:
            print(colored("Language must be EN or FA!", "red"))
            continue
        break

    # برگرداندن URL اصلی به جای نتیجه اعتبارسنجی
    return admin_ids, token, panel_url, lang, client_token

def set_config_in_db(db, admin_ids, token, url, lang, client_token):
    try:
        # Ensure URL has scheme
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # if str_config is not exists, create it
        if not db.select_str_config():
            db.add_str_config("bot_admin_id", value=json.dumps(admin_ids))
            db.add_str_config("bot_token_admin", value=token)
            db.add_str_config("bot_token_client", value=client_token)
            db.add_str_config("bot_lang", value=lang)
        else:
            db.edit_str_config("bot_admin_id", value=json.dumps(admin_ids))
            db.edit_str_config("bot_token_admin", value=token)
            db.edit_str_config("bot_token_client", value=client_token)
            db.edit_str_config("bot_lang", value=lang)

        # if servers is not exists, create it
        if not db.select_servers():
            db.add_server(url, 2000, title="Main Server", default_server=True)
        else:
            # find default server
            default_servers = db.find_server(default_server=True)
            if default_servers:
                default_server_id = default_servers[0]['id']
                default_server = default_servers[0]
                if default_server['url'] != url:
                    db.edit_server(default_server_id, url=url)
            else:
                db.add_server(url, 2000, title="Main Server", default_server=True)
    except Exception as e:
        logging.error(f"Error while inserting config to database \n Error:{e}")
        raise Exception(f"Error while inserting config to database \nBe in touch with {HIDY_BOT_ID}")

def print_current_conf(conf, server_url):
    print()
    print(colored("Current configration data:", "yellow"))
    print(f"[+] Admin IDs: {conf['bot_admin_id']}")
    print(f"[+] Admin Bot Token: {conf['bot_token_admin']}")
    print(f"[+] Client Bot Token: {conf['bot_token_client']}")
    print(f"[+] Panel URL: {server_url}")
    print(f"[+] Language: {conf['bot_lang']}")
    print()

if __name__ == '__main__':
    db = UserDBManager(USERS_DB_LOC)
    conf = load_config(db)
    server_url = load_server_url(db)
    if conf['bot_admin_id'] and conf['bot_token_admin'] and conf['bot_lang'] and server_url:
        print("Config is already set!")
        print_current_conf(conf, server_url)
        print("Do you want to change config? (y/n): ")
        if input().lower() == "y":
            admin_ids, token, url, lang, client_token = set_by_user()
            set_config_in_db(db, admin_ids, token, url, lang, client_token)
            conf = load_config(db)
            server_url = load_server_url(db)
    else:
        admin_ids, token, url, lang, client_token = set_by_user()
        set_config_in_db(db, admin_ids, token, url, lang, client_token)
        conf = load_config(db)
        server_url = load_server_url(db)
        
    try:
        set_config_variables(conf, server_url)
        print(colored("Configuration successfully loaded.", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))
        print(colored("Please restart the config.py script and try again.", "yellow"))
        sys.exit(1)
        
    # close database connection
    db.close()
else:
    # Initialize database and load config only when imported as a module
    db = UserDBManager(USERS_DB_LOC)
    conf = load_config(db)
    server_url = load_server_url(db)
    
    try:
        set_config_variables(conf, server_url)
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))
        print(colored("Please make sure config.py has been run at least once to set up the configuration.", "yellow"))
        # در اینجا exception را دوباره raise نمی‌کنیم تا برنامه بتواند ادامه یابد
    
    db.close()


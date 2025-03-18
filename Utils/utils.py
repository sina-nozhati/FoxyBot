# Description: API for connecting to the panel
import json
import logging
import os
import random
import string
from io import BytesIO
import re
from datetime import datetime
from urllib.parse import urlparse
from Database.dbManager import USERS_DB
import psutil
import qrcode
import requests
from config import PANEL_URL, BACKUP_LOC, CLIENT_TOKEN, USERS_DB_LOC,RECEIPTIONS_LOC,BOT_BACKUP_LOC, API_PATH,LOG_DIR,PROXY_PATH
import AdminBot.templates
from Utils import api
from version import __version__
import zipfile
import shutil
# Global variables
# Make Session for requests
session = requests.session()
# Base panel URL - example: https://panel.example.com
BASE_URL = urlparse(PANEL_URL).scheme + "://" + urlparse(PANEL_URL).netloc


# Users directory in panel
# USERS_DIR = "/admin/user/"


# Get request - return request object
def get_request(url):
    logging.info(f"GET Request to {privacy_friendly_logging_request(url)}")
    global session
    try:
        req = session.get(url)
        logging.info(f"GET Request to {privacy_friendly_logging_request(url)} - Status Code: {req.status_code}")
        return req
    except requests.exceptions.ConnectionError as e:
        logging.exception(f"Connection Exception: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logging.exception(f"Timeout Exception: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logging.exception(f"General Connection Exception: {e}")
        return False
    except Exception as e:
        logging.exception(f"General Exception: {e}")
        return False


# Post request - return request object
def post_request(url, data):
    logging.info(f"POST Request to {privacy_friendly_logging_request(url)} - Data: {data}")
    global session
    try:
        req = session.post(url, data=data)
        return req
    except requests.exceptions.ConnectionError as e:
        logging.exception(f"Connection Exception: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logging.exception(f"Timeout Exception: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logging.exception(f"General Connection Exception: {e}")
        return False
    except Exception as e:
        logging.exception(f"General Exception: {e}")
        return False


def users_to_dict(users_dict):
    if not users_dict:
        return False
    users_array = []
    for user in users_dict:
        users_array.append({
            'uuid': user['uuid'], 
            'name': user['name'], 
            'last_online': user['last_online'],
            'expiry_time': None,
            'usage_limit_GB': user['usage_limit_GB'], 
            'package_days': user['package_days'],
            'mode': user['mode'],
            'monthly': None, 
            'start_date': user['start_date'],
            'current_usage_GB': user['current_usage_GB'],
            'last_reset_time': user['last_reset_time'], 
            'comment': user['comment'],
            'telegram_id': user['telegram_id'],
            'added_by': user['added_by_uuid'], 
            'max_ips': None, 
            'enable': user.get('enable', True),
            'is_active': user.get('is_active', True),
            'lang': user.get('lang'),
            'ed25519_private_key': user.get('ed25519_private_key'),
            'ed25519_public_key': user.get('ed25519_public_key'),
            'wg_pk': user.get('wg_pk'),
            'wg_psk': user.get('wg_psk'),
            'wg_pub': user.get('wg_pub')
        })
    return users_array


# Change telegram user data format
def Telegram_users_to_dict(Tel_users_dict):
    if not Tel_users_dict:
        return False
    users_array = []
    for user in Tel_users_dict:
        users_array.append({'id': user[0], 'telegram_id': user[1], 'created_at': user[3], })
    return users_array


# Calculate remaining days
def calculate_remaining_days(start_date, package_days):
    import datetime
    import pytz

    datetime_iran = datetime.datetime.now(pytz.timezone('Asia/Tehran'))
    datetime_iran = datetime_iran.replace(tzinfo=None)
    if start_date is None:
        return package_days
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    # remaining_days = package_days - (datetime.datetime.now() - start_date).days
    remaining_days = package_days - (datetime_iran - start_date).days + 1
    if remaining_days < 0:
        return 0
    return remaining_days


# Calculate remaining usage
def calculate_remaining_usage(usage_limit_GB, current_usage_GB):
    remaining_usage = usage_limit_GB - current_usage_GB
    return round(remaining_usage, 2)


# Calculate last online time
def calculate_remaining_last_online(last_online_date_time):
    import datetime
    if last_online_date_time == "0001-01-01 00:00:00" or last_online_date_time == "1-01-01 00:00:00" or not last_online_date_time:
        return AdminBot.content.MESSAGES['NEVER']
    try:
        last_online_date_time = datetime.datetime.strptime(last_online_date_time, "%Y-%m-%d %H:%M:%S")
        last_online_time = (datetime.datetime.now() - last_online_date_time)
        last_online = AdminBot.templates.last_online_time_template(last_online_time)
        return last_online
    except ValueError:
        return AdminBot.content.MESSAGES['NEVER']


# Process users data - return list of users
def dict_process(url, users_dict, sub_id=None, server_id=None, custom_proxy_path=None):
    # استخراج بخش‌های URL
    parsed_url = urlparse(url)
    BASE_URL = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # اگر مسیر پروکسی سفارشی ارسال شده باشد از آن استفاده می‌کنیم
    if custom_proxy_path:
        PROXY_PATH = custom_proxy_path
    else:
        # در غیر این صورت از URL استخراج می‌کنیم
        path_parts = [part for part in parsed_url.path.split("/") if part]
        PROXY_PATH = path_parts[0] if len(path_parts) > 0 else None
    
    logging.info(f"Parse users page. Found {len(users_dict)} users.")
    print(f"Processing users data with BASE_URL={BASE_URL}, PROXY_PATH={PROXY_PATH}")
    
    if not users_dict:
        print("No users found to process")
        return False
        
    users_list = []
    for user in users_dict:
        # لاگ برای دیباگ
        print(f"Processing user {user.get('name', 'Unknown')} with UUID: {user.get('uuid', 'Unknown')}")
        
        # بررسی فیلدهای الزامی
        if 'uuid' not in user:
            print(f"User missing UUID. Skipping: {user}")
            continue
            
        # بررسی وجود فیلدهای اصلی و پر کردن مقادیر پیش‌فرض
        usage_limit = user.get('usage_limit_GB', 0)
        if usage_limit is None:
            usage_limit = 0
            
        current_usage = user.get('current_usage_GB', 0)
        if current_usage is None:
            current_usage = 0
            
        package_days = user.get('package_days', 0)
        if package_days is None:
            package_days = 0
            
        # ساخت داده‌های کاربر با ساختار استاندارد
        user_data = {
            "name": user.get('name', 'Unknown'),
            "usage": {
                'usage_limit_GB': round(usage_limit, 2),
                'current_usage_GB': round(current_usage, 2),
                'remaining_usage_GB': calculate_remaining_usage(usage_limit, current_usage)
            },
            "remaining_day": calculate_remaining_days(user.get('start_date'), package_days),
            "comment": user.get('comment', "") or "",
            "last_connection": calculate_remaining_last_online(user.get('last_online')) if user.get('last_online') else None,
            "uuid": user['uuid'],
            "link": f"{BASE_URL}/{PROXY_PATH}/{user['uuid']}/" if PROXY_PATH else f"{BASE_URL}/{user['uuid']}/",
            "mode": user.get('mode', 'unknown'),
            "enable": user.get('enable', True),
            "is_active": user.get('is_active', True),
            "lang": user.get('lang', 'fa'),
            "sub_id": sub_id,
            "server_id": server_id
        }
        
        users_list.append(user_data)

    print(f"Successfully processed {len(users_list)} users")
    return users_list


# Get single user info - return dict of user info
def user_info(url, uuid):
    logging.info(f"Get info of user single user - {uuid}")
    lu = api.select(url)
    if not lu:
        return False
    for user in lu:
        if user['uuid'] == uuid:
            return user
    return False


# Get sub links - return dict of sub links
def sub_links(uuid, url=None):
    """
    دریافت لینک‌های اشتراک کاربر با استفاده از سیستم هوشمند تشخیص مسیر پروکسی
    
    Args:
        uuid: UUID کاربر
        url: آدرس سرور (اختیاری)
        
    Returns:
        dict: لینک‌های اشتراک کاربر
    """
    server_id = None
    telegram_id = None
    order_id = None
    subscription_type = None
    
    # یافتن اطلاعات اشتراک
    non_order_users = USERS_DB.find_non_order_subscription(uuid=uuid)
    order_users = USERS_DB.find_order_subscription(uuid=uuid)
    
    if order_users:
        order_user = order_users[0]
        server_id = order_user['server_id']
        order_id = order_user['order_id']
        subscription_type = 'order'
        
        # یافتن telegram_id مربوط به این سفارش
        orders = USERS_DB.find_order(id=order_id)
        if orders:
            telegram_id = orders[0]['telegram_id']
            
    elif non_order_users:
        non_order_user = non_order_users[0]
        server_id = non_order_user['server_id']
        telegram_id = non_order_user['telegram_id']
        subscription_type = 'non_order'
        
    # اگر URL به صورت دستی تنظیم نشده باشد، سعی می‌کنیم از دیتابیس بخوانیم
    if not url and server_id:
        servers = USERS_DB.find_server(id=server_id)
        if servers:
            server = servers[0]
            url = server['url']
    
    # در صورتی که هنوز تلگرام آیدی یافت نشده، از طریق سفارش پیدا کنیم
    if not telegram_id and order_id:
        orders = USERS_DB.find_order(id=order_id)
        if orders:
            telegram_id = orders[0]['telegram_id']
    
    # اگر هیچ اطلاعاتی یافت نشد، برگشت به روش قدیمی
    if not url or not server_id or not telegram_id or not subscription_type:
        BASE_URL = urlparse(url).scheme + "://" + urlparse(url).netloc
        logging.info(f"Using old method for sub links - {uuid}")
        sub = {}
        PANEL_DIR = urlparse(url).path.split('/')
        proxy_path = PANEL_DIR[-2] if len(PANEL_DIR) >= 2 else ""
        
        # Clash open app: clash://install-config?url=
        # Hidden open app: clashmeta://install-config?url=
        sub['clash_configs'] = f"{BASE_URL}/{proxy_path}/{uuid}/clash/all.yml"
        sub['hiddify_configs'] = f"{BASE_URL}/{proxy_path}/{uuid}/clash/meta/all.yml"
        sub['sub_link'] = f"{BASE_URL}/{proxy_path}/{uuid}/all.txt"
        sub['sub_link_b64'] = f"{BASE_URL}/{proxy_path}/{uuid}/all.txt?base64=True"
        sub['sub_link_auto'] = f"{BASE_URL}/{proxy_path}/{uuid}/auto"
        sub['sing_box'] = f"{BASE_URL}/{proxy_path}/{uuid}/singbox/config.json"
        sub['sing_box_full'] = f"{BASE_URL}/{proxy_path}/{uuid}/singbox/full.json"
        
        return sub
    
    # استفاده از سیستم هوشمند برای دریافت مسیر پروکسی
    identifier = order_id if subscription_type == 'order' else telegram_id
    
    logging.info(f"Getting subscription info for user {telegram_id} with UUID {uuid}")
    subscription_info = get_user_subscription_info(
        USERS_DB=USERS_DB,
        telegram_id=telegram_id,
        uuid=uuid,
        subscription_type=subscription_type,
        identifier=identifier
    )
    
    if not subscription_info:
        # اگر اطلاعات اشتراک یافت نشد، از روش قدیمی استفاده می‌کنیم
        logging.warning(f"Could not get subscription info, using old method for {uuid}")
        BASE_URL = urlparse(url).scheme + "://" + urlparse(url).netloc
        sub = {}
        PANEL_DIR = urlparse(url).path.split('/')
        proxy_path = PANEL_DIR[-2] if len(PANEL_DIR) >= 2 else ""
    else:
        # استفاده از مسیر پروکسی یافت شده
        proxy_path = subscription_info['proxy_path']
        BASE_URL = urlparse(subscription_info['server_url']).scheme + "://" + urlparse(subscription_info['server_url']).netloc
        logging.info(f"Using smart proxy path {proxy_path} for user {telegram_id} with UUID {uuid}")
    
    # ساخت لینک‌های اشتراک
    sub = {}
    sub['clash_configs'] = f"{BASE_URL}/{proxy_path}/{uuid}/clash/all.yml"
    sub['hiddify_configs'] = f"{BASE_URL}/{proxy_path}/{uuid}/clash/meta/all.yml"
    sub['sub_link'] = f"{BASE_URL}/{proxy_path}/{uuid}/all.txt"
    sub['sub_link_b64'] = f"{BASE_URL}/{proxy_path}/{uuid}/all.txt?base64=True"
    sub['sub_link_auto'] = f"{BASE_URL}/{proxy_path}/{uuid}/auto"
    sub['sing_box'] = f"{BASE_URL}/{proxy_path}/{uuid}/singbox/config.json"
    sub['sing_box_full'] = f"{BASE_URL}/{proxy_path}/{uuid}/singbox/full.json"
    
    return sub


# Parse sub links
def sub_parse(sub):
    logging.info(f"Parse sub links")
    res = get_request(sub)
    if not res or res.status_code != 200:
        return False

    urls = re.findall(r'(vless:\/\/[^\n]+)|(vmess:\/\/[^\n]+)|(trojan:\/\/[^\n]+)', res.text)

    config_links = {
        'vless': [],
        'vmess': [],
        'trojan': []
    }
    for url in urls:
        if url[0]:
            match = re.search(r'#(.+)$', url[0])
            if match:
                vless_title = match.group(1).replace("%20", " ")
                config_links['vless'].append([url[0], vless_title])
        elif url[1]:
            config = url[1].replace("vmess://", "")
            config_parsed = base64decoder(config)
            if config_parsed:
                vmess_title = config_parsed['ps'].replace("%20", " ")
                config_links['vmess'].append([url[1], vmess_title])
        elif url[2]:
            match = re.search(r'#(.+)$', url[2])
            if match:
                trojan_title = match.group(1).replace("%20", " ")
                trojan_sni = re.search(r'sni=([^&]+)', url[2])
                if trojan_sni:
                    if trojan_sni.group(1) == "fake_ip_for_sub_link":
                        continue
                config_links['trojan'].append([url[2], match.group(1)])
        
    return config_links


# Backup panel
def backup_panel(url):
    logging.info(f"Backup panel")
    BASE_URL = urlparse(url,).scheme + "://" + urlparse(url,).netloc
    dir_panel = urlparse(url).path.split('/')
    backup_url = f"{BASE_URL}/{dir_panel[1]}/{dir_panel[2]}/admin/backup/backupfile/"

    backup_req = get_request(backup_url)
    if not backup_req or backup_req.status_code != 200:
        return False

    now = datetime.now()
    file_name = f"backup_{now.strftime('%Y-%m-%d_%H-%M-%S')}.json"
    with open(os.path.join(BACKUP_LOC, file_name), 'wb') as f:
        f.write(backup_req.content)
    return True

# zip an array of files
def zip_files(files, zip_file_name,path=None):
    if path:
        zip_file_name = os.path.join(path, zip_file_name)
    with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            # Get the base name of the file (i.e. the file name without the parent folders)
            base_name = os.path.basename(file)
            # Write the file to the zip archive with the base name as the arcname
            zip_file.write(file, arcname=base_name)
    return zip_file_name

# full backup
def full_backup():
    files = []
    servers = USERS_DB.select_servers()
    for server in servers:
        file_name = backup_panel(server['url'])
        if file_name:
            files.append(file_name)
    backup_bot = backup_json_bot()
    if backup_bot:
        files.append(backup_bot)
    if files:
        now = datetime.now()
        dt_string = now.strftime("%d-%m-%Y_%H-%M-%S")
        zip_title = f"Backup_{dt_string}.zip"
        zip_file_name = zip_files(files, zip_title,path=BACKUP_LOC)
        if zip_file_name:
            return zip_file_name
    return False

# Extract UUID from config
def extract_uuid_from_config(config):
    logging.info(f"Extract UUID from config")
    uuid_pattern = r"([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})"
    match = re.search(uuid_pattern, config)

    if match:
        uuid = match.group(1)
        return uuid
    else:
        return None


# System status
def system_status():
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    return {
        'cpu': cpu_usage,
        'ram': ram_usage,
        'disk': disk_usage
    }


# Search user by name
def search_user_by_name(url, name):
    # users = dict_process(users_to_dict(ADMIN_DB.select_users()))
    users = api.select(url)
    if not users:
        return False
    res = []
    for user in users:
        if name.lower() in user['name'].lower():
            res.append(user)
    if res:
        return res
    return False


# Search user by uuid
def search_user_by_uuid(url, uuid):
    # users = dict_process(users_to_dict(ADMIN_DB.select_users()))
    users = api.select(url)
    if not users:
        return False
    for user in users:
        if user['uuid'] == uuid:
            return user
    return False


# Base64 decoder
def base64decoder(s):
    import base64
    try:
        conf = base64.b64decode(s).decode("utf-8")
        conf = json.loads(conf)
    except Exception as e:
        conf = False

    return conf


# Search user by config
def search_user_by_config(url, config):
    if config.startswith("vmess://"):
        config = config.replace("vmess://", "")
        config = base64decoder(config)
        if config:
            uuid = config['id']
            user = search_user_by_uuid(url, uuid)
            if user:
                return user
    uuid = extract_uuid_from_config(config)
    if uuid:
        user = search_user_by_uuid(url, uuid)
        if user:
            return user
    return False


# Check text is it config or sub
def is_it_config_or_sub(config):
    if config.startswith("vmess://"):
        config = config.replace("vmess://", "")
        config = base64decoder(config)
        if config:
            return config['id']
    uuid = extract_uuid_from_config(config)
    if uuid:
        return uuid


# Users bot add plan
def users_bot_add_plan(size, days, price, server_id,description=None):
    if not CLIENT_TOKEN:
        return False
    # randon 4 digit number
    plan_id = random.randint(10000, 99999)
    plan_status = USERS_DB.add_plan(plan_id, size, days, price, server_id,description=description)
    if not plan_status:
        return False
    return True

#--------------------------Server area ----------------------------
# add server
def add_server(url, user_limit, title=None, description=None, status=True, default_server=False):
    # randon 5 digit number
    #server_id = random.randint(10000, 99999)
    server_status = USERS_DB.add_server(url, user_limit, title, description, status, default_server)
    if not server_status:
        return False
    return True


# Check user is expired
def is_user_expired(user):
    if user['remaining_day'] == 0:
        return True
    return False


# Expired users list
def expired_users_list(users):
    expired_users = []
    for user in users:
        if is_user_expired(user):
            expired_users.append(user)
    return expired_users


# Text to QR code
def txt_to_qr(txt):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr.add_data(txt)
    qr.make(fit=True, )
    img_qr = qr.make_image(fill_color="black", back_color="white")
    stream = BytesIO()
    img_qr.save(stream)
    img = stream.getvalue()

    return img


# List of users who not ordered from bot (Link Subscription)
def non_order_user_info(telegram_id):
    users_list = []
    non_ordered_subscriptions = USERS_DB.find_non_order_subscription(telegram_id=telegram_id)
    if non_ordered_subscriptions:
        for subscription in non_ordered_subscriptions:
            server_id = subscription['server_id']
            server = USERS_DB.find_server(id=server_id)
            if server:
                server = server[0]
                #if server['status']:
                URL = server['url'] + API_PATH
                non_order_user = api.find(URL, subscription['uuid'])
                if non_order_user:
                    # دریافت مسیر پروکسی ذخیره شده در دیتابیس
                    proxy_path = subscription.get('proxy_path')
                    logging.info(f"Using proxy_path from DB: {proxy_path} for UUID: {subscription['uuid']}")
                    
                    non_order_user = users_to_dict([non_order_user])
                    # ارسال مسیر پروکسی به تابع dict_process
                    non_order_user = dict_process(URL, non_order_user, subscription['id'], server_id, custom_proxy_path=proxy_path)
                    if non_order_user:
                        non_order_user = non_order_user[0]
                        # اضافه کردن اطلاعات مسیر پروکسی به اطلاعات کاربر
                        non_order_user['proxy_path'] = proxy_path
                        users_list.append(non_order_user)
    return users_list


# List of users who ordered from bot and made payment
def order_user_info(telegram_id):
    users_list = []
    orders = USERS_DB.find_order(telegram_id=telegram_id)
    if orders:
        for order in orders:
            ordered_subscriptions = USERS_DB.find_order_subscription(order_id=order['id'])
            if ordered_subscriptions:
                for subscription in ordered_subscriptions:
                    server_id = subscription['server_id']
                    server = USERS_DB.find_server(id=server_id)
                    if server:
                        server = server[0]
                        #if server['status']:
                        URL = server['url'] + API_PATH
                        order_user = api.find(URL, subscription['uuid'])
                        if order_user:
                            # دریافت مسیر پروکسی ذخیره شده در دیتابیس
                            proxy_path = subscription.get('proxy_path')
                            logging.info(f"Using proxy_path from DB: {proxy_path} for UUID: {subscription['uuid']}")
                            
                            order_user = users_to_dict([order_user])
                            # ارسال مسیر پروکسی به تابع dict_process
                            order_user = dict_process(URL, order_user, subscription['id'], server_id, custom_proxy_path=proxy_path)
                            if order_user:
                                order_user = order_user[0]
                                # اضافه کردن اطلاعات مسیر پروکسی به اطلاعات کاربر
                                order_user['proxy_path'] = proxy_path
                                users_list.append(order_user)
    return users_list



# Replace last three characters of a string with random numbers (For Payment)
def replace_last_three_with_random(input_string):
    if len(input_string) <= 3:
        return input_string  # Not enough characters to replace
    input_string = int(input_string)
    input_string += random.randint(1000, 9999)
    return str(input_string)
    # random_numbers = ''.join(random.choice(string.digits) for _ in range(3))
    # modified_string = input_string[:-3] + random_numbers
    # return modified_string


# Privacy-friendly logging - replace your panel url with panel.private.com
def privacy_friendly_logging_request(url):
    url = urlparse(url)
    url = url.scheme + "://" + "panel.private.com" + url.path
    return url


def all_configs_settings():
    bool_configs = USERS_DB.select_bool_config()
    int_configs = USERS_DB.select_int_config()
    str_configs = USERS_DB.select_str_config()

    # all configs to one dict
    all_configs = {}
    for config in bool_configs:
        all_configs[config['key']] = config['value']
    for config in int_configs:
        all_configs[config['key']] = config['value']
    for config in str_configs:
        all_configs[config['key']] = config['value']
    return all_configs


def find_order_subscription_by_uuid(uuid):
    order_subscription = USERS_DB.find_order_subscription(uuid=uuid)
    non_order_subscription = USERS_DB.find_non_order_subscription(uuid=uuid)
    if order_subscription:
        return order_subscription[0]
    elif non_order_subscription:
        return non_order_subscription[0]
    else:
        return False
    
def is_it_subscription_by_uuid_and_telegram_id(uuid, telegram_id):
    subs = []
    flag = False
    orders = USERS_DB.find_order(telegram_id=telegram_id)
    if orders:
        for order in orders:
            ordered_subscriptions = USERS_DB.find_order_subscription(order_id=order['id'])
            if ordered_subscriptions:
                for subscription in ordered_subscriptions:
                    if subscription['uuid'] == uuid:
                        flag = True
                        subs.append(subscription)
                        break
            if flag == True:
                break 
    
    non_order_subscriptions = USERS_DB.find_non_order_subscription(telegram_id=telegram_id)
    if non_order_subscriptions:
        for subscription in non_order_subscriptions:
            if subscription['uuid'] == uuid:
                subs.append(subscription)
                break
    if subs:
        return True
    else:
        return False


def toman_to_rial(toman):
    return int(toman) * 10


def rial_to_toman(rial):
    return "{:,.0f}".format(int(int(rial) / 10))


def backup_json_bot():
    back_dir = BOT_BACKUP_LOC
    if not os.path.exists(back_dir):
        os.makedirs(back_dir)
    bk_json_data = USERS_DB.backup_to_json(back_dir)
    if not bk_json_data:
        return False
    bk_json_data['version'] = __version__
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H-%M-%S")
    bk_json_file = os.path.join(back_dir, f"Backup_Bot_{dt_string}.json")
    with open(bk_json_file, 'w+') as f:
        json.dump(bk_json_data, f, indent=4)
    zip_file = os.path.join(back_dir, f"Backup_Bot_{dt_string}.zip")
    with zipfile.ZipFile(zip_file, 'w') as zip:
        zip.write(bk_json_file,os.path.basename(bk_json_file))
        zip.write(USERS_DB_LOC,os.path.basename(USERS_DB_LOC))
        for file in os.listdir(RECEIPTIONS_LOC):
            zip.write(os.path.join(RECEIPTIONS_LOC, file),os.path.join(os.path.basename(RECEIPTIONS_LOC),file))
    os.remove(bk_json_file)
    return zip_file


def restore_json_bot(file):
    extract_path = os.path.join(BOT_BACKUP_LOC, "tmp", os.path.basename(file).replace(".zip", ""))
    if not os.path.exists(file):
        return False
    if not file.endswith(".zip"):
        return False
    try:
        if not os.path.exists(extract_path):
            os.makedirs(extract_path)
    except Exception as e:
        logging.exception(f"Exception: {e}")
        return False
    try:
        with zipfile.ZipFile(file, 'r') as outer_zip:
            # Iterate through all entries in the outer zip
            for entry in outer_zip.namelist():
                # Check if the entry is a zip file
                if entry.lower().endswith('.zip'):
                    nested_zip_filename = entry
                    # Extract the nested zip file
                    with outer_zip.open(nested_zip_filename) as nested_zip_file:
                        # Save the nested zip file to a temporary location
                        nested_zip_path = os.path.join(extract_path, nested_zip_filename)
                        with open(nested_zip_path, 'wb') as f:
                            f.write(nested_zip_file.read())

                        # Extract contents of the nested zip file
                        with zipfile.ZipFile(nested_zip_path, 'r') as nested_zip:
                            # Check if the JSON file exists
                            # select json file
                            json_filename = None
                            for file in nested_zip.namelist():
                                if file.endswith('.json'):
                                    json_filename = file
                                    break
                            if json_filename in nested_zip.namelist():
                                nested_zip.extractall(extract_path)
                else:
                            json_filename = None
                            for file in outer_zip.namelist():
                                if file.endswith('.json'):
                                    json_filename = file
                                    break
                            if json_filename in outer_zip.namelist():
                                outer_zip.extractall(extract_path)
    except Exception as e:
        logging.exception(f"Exception: {e}")
        return False
                
            
    bk_json_file = os.path.join(extract_path, os.path.basename(json_filename))
    # with open(bk_json_file, 'r') as f:
    #     bk_json_data = json.load(f)
    status_db = USERS_DB.restore_from_json(bk_json_file)
    if not status_db:
        return False
    if not os.path.exists(os.path.join(extract_path, os.path.basename(RECEIPTIONS_LOC))):
        os.mkdir(os.path.join(extract_path, os.path.basename(RECEIPTIONS_LOC)))
    # move reception files
    for file in os.listdir(os.path.join(extract_path, os.path.basename(RECEIPTIONS_LOC))):
        try:
            os.rename(os.path.join(extract_path, os.path.basename(RECEIPTIONS_LOC), file),
                    os.path.join(RECEIPTIONS_LOC, file))
        except Exception as e:
            logging.exception(f"Exception: {e}")
    try:
        # # remove tmp folder
        # os.remove(bk_json_file)
        # # remove RECEIPTIONS all files
        # for file in os.listdir(os.path.join(extract_path, os.path.basename(RECEIPTIONS_LOC))):
        #     os.remove(os.path.join(extract_path, os.path.basename(RECEIPTIONS_LOC), file))
        # os.rmdir(os.path.join(extract_path, os.path.basename(RECEIPTIONS_LOC)))
        # # romove hidyBot.db
        # os.remove(os.path.join(extract_path, os.path.basename(USERS_DB_LOC)))
        shutil.rmtree(extract_path)
    except Exception as e:
        logging.exception(f"Exception: {e}")
        return False
    return True

# Debug Data 
def debug_data():
    bk_json_data = USERS_DB.backup_to_json(BOT_BACKUP_LOC)
    if not bk_json_data:
        return False
    
    bk_json_data['version'] = __version__
    
    new_servers = []
    for server in bk_json_data['servers']:
        url = privacy_friendly_logging_request(server['url'])
        server['url'] = url
        new_servers.append(server)
    bk_json_data['servers'] = new_servers
    
    bk_json_data['str_config'] = [x for x in bk_json_data['str_config'] if x['key'] not in ['bot_token_admin','bot_token_client']]
    
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H-%M-%S")
    bk_json_file = os.path.join(BOT_BACKUP_LOC, f"DB_Data_{dt_string}.json")
    with open(bk_json_file, 'w+') as f:
        json.dump(bk_json_data, f, indent=4)
    zip_file = os.path.join(BOT_BACKUP_LOC, f"Debug_Data_{dt_string}.zip")
    with zipfile.ZipFile(zip_file, 'w') as zip:
        zip.write(bk_json_file,os.path.basename(bk_json_file))
        if os.path.exists(os.path.join(os.getcwd(),"bot.log")):
            # only send last 1000 lines of log
            with open(os.path.join(os.getcwd(),"bot.log"), 'r') as f:
                lines = f.readlines()
                lines = lines[-1000:]
                with open(os.path.join(os.getcwd(),"bot.log"), 'w') as f:
                    f.writelines(lines)
            zip.write("bot.log",os.path.basename("bot.log"))
        if os.path.exists(LOG_DIR):
            for file in os.listdir(LOG_DIR):
                zip.write(os.path.join(LOG_DIR, file),file)

    os.remove(bk_json_file)
    return zip_file
    

def test_proxy_path(server_url, proxy_path, api_key, user_uuid):
    """
    تست اعتبار مسیر پروکسی کاربر با تلاش برای دسترسی به کانفیگ‌های کاربر
    
    Args:
        server_url: آدرس سرور
        proxy_path: مسیر پروکسی کاربر
        api_key: کلید API
        user_uuid: UUID کاربر
        
    Returns:
        bool: آیا مسیر معتبر است یا خیر
    """
    try:
        headers = {"Hiddify-API-Key": api_key}
        
        # تلاش برای دسترسی به کانفیگ‌های کاربر با مسیر پروکسی
        response = requests.get(
            f"{server_url}/{proxy_path}/{user_uuid}/api/v2/user/all-configs/",
            headers=headers,
            timeout=10
        )
        
        # بررسی وضعیت پاسخ
        if response.status_code == 200:
            return True
            
        # اگر مسیر بدون UUID کار کند
        response = requests.get(
            f"{server_url}/{proxy_path}/api/v2/user/all-configs/",
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 200
    except:
        return False


def get_user_subscription_info(USERS_DB, telegram_id, uuid, subscription_type, identifier):
    """
    دریافت اطلاعات اشتراک کاربر با استفاده از استراتژی هوشمند
    
    Args:
        USERS_DB: شیء دیتابیس
        telegram_id: شناسه تلگرام کاربر
        uuid: UUID کاربر
        subscription_type: نوع اشتراک ('order' یا 'non_order')
        identifier: شناسه اشتراک (order_id یا telegram_id)
        
    Returns:
        dict: اطلاعات اشتراک کاربر شامل proxy_path و uuid
    """
    # یافتن اطلاعات کاربر
    user = USERS_DB.find_user(telegram_id=telegram_id)
    if not user:
        logging.error(f"User {telegram_id} not found in database")
        return None
    
    try:
        # یافتن سرور مربوط به اشتراک
        if subscription_type == 'order':
            order_sub = USERS_DB.find_order_subscription(order_id=identifier)
            if not order_sub:
                logging.error(f"Order subscription {identifier} not found")
                return None
            server_id = order_sub['server_id']
        elif subscription_type == 'non_order':
            non_order_sub = USERS_DB.find_non_order_subscription(telegram_id=identifier, uuid=uuid)
            if not non_order_sub:
                logging.error(f"Non-order subscription for user {identifier} with UUID {uuid} not found")
                return None
            server_id = non_order_sub['server_id']
        else:
            logging.error(f"Invalid subscription type: {subscription_type}")
            return None
            
        # یافتن اطلاعات سرور
        server = USERS_DB.find_server(id=server_id)
        if not server:
            logging.error(f"Server {server_id} not found")
            return None
            
        # بررسی اگر مسیر پروکسی در دیتابیس ذخیره شده است
        proxy_path = USERS_DB.get_subscription_proxy_path(subscription_type, identifier, uuid)
        if proxy_path:
            # تست اعتبار مسیر پروکسی
            if test_proxy_path(server['url'], proxy_path, server['api_key'], uuid):
                logging.info(f"Using stored proxy path {proxy_path} for user {telegram_id}")
                return {
                    'proxy_path': proxy_path,
                    'uuid': uuid,
                    'server_url': server['url'],
                    'server_api_key': server['api_key']
                }
        
        # اگر مسیر در دیتابیس نباشد یا نامعتبر باشد، از API ادمین استفاده می‌کنیم
        admin_proxy_path = server.get('proxy_path')
        if not admin_proxy_path:
            # اگر مسیر پروکسی ادمین در سرور ذخیره نشده باشد، از URL سرور استخراج می‌کنیم
            parsed_url = urlparse(server['url'])
            path_parts = [part for part in parsed_url.path.split("/") if part]
            if path_parts and len(path_parts) > 0:
                admin_proxy_path = path_parts[0]
            else:
                logging.error(f"Could not extract admin proxy path from server URL: {server['url']}")
                return None
        
        # دریافت اطلاعات کاربر از API ادمین
        try:
            user_info = api.get_user(
                proxy_path=admin_proxy_path,
                api_key=server['api_key'],
                uuid=uuid
            )
            
            if user_info and "secret_uuid" in user_info:
                # یافتن secret_uuid کاربر
                secret_uuid = user_info["secret_uuid"]
                if secret_uuid != uuid:
                    # تست اعتبار secret_uuid به عنوان مسیر پروکسی
                    if test_proxy_path(server['url'], secret_uuid, server['api_key'], uuid) or test_proxy_path(server['url'], admin_proxy_path, server['api_key'], secret_uuid):
                        # ذخیره secret_uuid در دیتابیس برای استفاده‌های بعدی
                        USERS_DB.update_subscription_proxy_path(
                            subscription_type=subscription_type,
                            identifier=identifier,
                            uuid=uuid,
                            proxy_path=secret_uuid
                        )
                        
                        logging.info(f"Found and saved secret_uuid {secret_uuid} as proxy path for user {telegram_id}")
                        return {
                            'proxy_path': secret_uuid,
                            'uuid': uuid,
                            'server_url': server['url'],
                            'server_api_key': server['api_key']
                        }
        except Exception as e:
            logging.error(f"Error getting user info from admin API: {e}")
            # اگر خطا رخ داد، به روش‌های دیگر ادامه می‌دهیم
        
        # استفاده از تابع هوشمند get_user_proxy_path
        try:
            user_proxy_path = api.get_user_proxy_path(
                hiddify_panel_url=server['url'],
                admin_proxy_path=admin_proxy_path,
                api_key=server['api_key'],
                user_uuid=uuid
            )
            
            if user_proxy_path and user_proxy_path != admin_proxy_path:
                # تست اعتبار مسیر پروکسی
                if test_proxy_path(server['url'], user_proxy_path, server['api_key'], uuid):
                    # ذخیره مسیر پروکسی در دیتابیس
                    USERS_DB.update_subscription_proxy_path(
                        subscription_type=subscription_type,
                        identifier=identifier,
                        uuid=uuid,
                        proxy_path=user_proxy_path
                    )
                    
                    logging.info(f"Found and saved proxy path {user_proxy_path} for user {telegram_id}")
                    return {
                        'proxy_path': user_proxy_path,
                        'uuid': uuid,
                        'server_url': server['url'],
                        'server_api_key': server['api_key']
                    }
        except Exception as e:
            logging.error(f"Error getting user proxy path: {e}")
        
        # اگر هیچ روشی موفق نبود، از مسیر پروکسی ادمین استفاده می‌کنیم
        logging.warning(f"Using admin proxy path {admin_proxy_path} for user {telegram_id} as fallback")
        return {
            'proxy_path': admin_proxy_path,
            'uuid': uuid,
            'server_url': server['url'],
            'server_api_key': server['api_key']
        }
    except Exception as e:
        logging.error(f"Error in get_user_subscription_info: {e}")
        return None
    
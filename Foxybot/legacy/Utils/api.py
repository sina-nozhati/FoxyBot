# from config import *
# from Utils.utils import *
import json
import logging
from urllib.parse import urlparse
import datetime
import requests
from config import API_PATH
import Utils


# Document: https://github.com/hiddify/hiddify-config/discussions/3209
# تطبیق داده شده با API جدید Hiddify نسخه 2.2.0

def parse_panel_url(url):
    """
    استخراج proxy_path و API key از URL پنل
    مثال: https://panel.example.com/7frgemkvtE0/78854985-68dp-425c-989b-7ap0c6kr9bd4
    """
    # حذف اسلش آخر و تقسیم با اسلش
    parts = url.rstrip("/").split("/")
    
    # دو قسمت آخر باید proxy_path و api_key باشند
    if len(parts) >= 2:
        proxy_path = parts[-2]  # 7frgemkvtE0
        api_key = parts[-1]     # 78854985-68dp-425c-989b-7ap0c6kr9bd4
        return proxy_path, api_key
    else:
        logging.error("فرمت URL پنل نامعتبر است. فرمت صحیح: https://panel.example.com/proxy_path/api_key")
        return None, None

def select(url, endpoint="/user/"):
    """دریافت لیست تمام کاربران"""
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return None
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        headers = {"Hiddify-API-Key": api_key}
        response = requests.get(
            f"{base_url}/{proxy_path}/api/v2/admin/user/",
            headers=headers
        )
        response.raise_for_status()
        
        users = response.json()
        res = Utils.utils.dict_process(url, Utils.utils.users_to_dict(users))
        return res
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def find(url, uuid, endpoint="/user/"):
    """یافتن کاربر با UUID"""
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return None
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        headers = {"Hiddify-API-Key": api_key}
        response = requests.get(
            f"{base_url}/{proxy_path}/api/v2/admin/user/{uuid}/",
            headers=headers
        )
        
        if response.status_code == 404:
            # اگر کاربر پیدا نشد، همه کاربران را بررسی کنیم
            all_users_response = requests.get(
                f"{base_url}/{proxy_path}/api/v2/admin/user/",
                headers=headers
            )
            all_users_response.raise_for_status()
            all_users = all_users_response.json()
            
            # جستجو برای UUID
            for user in all_users:
                if user.get('uuid') == uuid:
                    return user
            return None
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def insert(url, name, usage_limit_GB, package_days, last_reset_time=None, added_by_uuid=None, mode="no_reset",
            last_online="1-01-01 00:00:00", telegram_id=None,
            comment=None, current_usage_GB=0, start_date=None, endpoint="/user/"):
    """ایجاد کاربر جدید"""
    import uuid as uuid_gen
    user_uuid = str(uuid_gen.uuid4())
    
    if not last_reset_time:
        last_reset_time = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if not start_date:
        start_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return None
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        # ساخت داده کاربر برای API جدید
        data = {
            "uuid": user_uuid,
            "name": name,
            "usage_limit_GB": usage_limit_GB,
            "package_days": package_days,
            "comment": comment if comment else "",
            "start_date": start_date,
            "current_usage_GB": current_usage_GB
        }
        
        headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
        response = requests.post(
            f"{base_url}/{proxy_path}/api/v2/admin/user/",
            headers=headers,
            json=data
        )
        
        if response.status_code == 422:
            error_detail = response.json().get("detail", {})
            logging.error(f"Validation error: {error_detail}")
            return None
            
        response.raise_for_status()
        return user_uuid
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def update(url, uuid, endpoint="/user/", **kwargs):
    """بروزرسانی کاربر موجود"""
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return None
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        # در API جدید، نیازی به دریافت اطلاعات قبلی برای بروزرسانی نیست
        # فقط فیلدهایی که باید تغییر کنند را ارسال می‌کنیم
        data = kwargs
        
        headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
        response = requests.patch(
            f"{base_url}/{proxy_path}/api/v2/admin/user/{uuid}/",
            headers=headers,
            json=data
        )
        
        if response.status_code == 422:
            error_detail = response.json().get("detail", {})
            logging.error(f"Validation error: {error_detail}")
            return None
            
        response.raise_for_status()
        return uuid
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def delete_user(url, uuid):
    """حذف کاربر با UUID"""
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return False
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        headers = {"Hiddify-API-Key": api_key}
        response = requests.delete(
            f"{base_url}/{proxy_path}/api/v2/admin/user/{uuid}/",
            headers=headers
        )
        
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error("API error: %s" % e)
        return False

def get_server_status(url):
    """دریافت وضعیت سرور"""
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return None
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        headers = {"Hiddify-API-Key": api_key}
        response = requests.get(
            f"{base_url}/{proxy_path}/api/v2/admin/server_status/",
            headers=headers
        )
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def get_user_configs(url, uuid):
    """دریافت کانفیگ‌های کاربر"""
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return None
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        headers = {"Hiddify-API-Key": api_key}
        # استفاده از مسیر جدید برای دریافت کانفیگ‌های کاربر در API جدید
        response = requests.get(
            f"{base_url}/{proxy_path}/api/v2/admin/user/{uuid}/configs/",
            headers=headers
        )
        
        if response.status_code == 404:
            # اگر نتیجه 404 بود، با روش دیگری تلاش کنیم
            response = requests.get(
                f"{base_url}/{proxy_path}/api/v2/user/all-configs/",
                headers=headers
            )
            
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error("API error: %s" % e)
        return None

def update_user_usage(url):
    """بروزرسانی آمار مصرف کاربران"""
    try:
        proxy_path, api_key = parse_panel_url(url)
        if not proxy_path or not api_key:
            return None
            
        base_url = url.rstrip("/").rsplit('/', 2)[0]  # حذف دو بخش آخر URL
        
        headers = {"Hiddify-API-Key": api_key}
        response = requests.get(
            f"{base_url}/{proxy_path}/api/v2/admin/update-user-usage/",
            headers=headers
        )
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error("API error: %s" % e)
        return None


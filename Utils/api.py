import requests
import json
import os
from requests.exceptions import HTTPError
from urllib.parse import urlparse
from datetime import datetime

# This will be set from config.py
HIDDIFY_PANEL_URL = ""

def set_panel_url(url):
    """Set the base panel URL (without proxy_path and api_key)"""
    global HIDDIFY_PANEL_URL
    # Remove trailing slashes
    HIDDIFY_PANEL_URL = url.rstrip("/")

def parse_panel_url(url):
    """
    Parse Hiddify panel URL to extract proxy_path and API key
    Example: https://panel.example.com/7frgemkvtE0/78854985-68dp-425c-989b-7ap0c6kr9bd4
    Returns: proxy_path, api_key
    """
    # Remove trailing slashes and split by /
    parts = url.rstrip("/").split("/")
    
    # The last two parts should be proxy_path and api_key
    if len(parts) >= 2:
        proxy_path = parts[-2]  # 7frgemkvtE0
        api_key = parts[-1]     # 78854985-68dp-425c-989b-7ap0c6kr9bd4
        return proxy_path, api_key
    else:
        raise ValueError("Invalid panel URL format. Expected format: https://panel.example.com/proxy_path/api_key")

def get_users(proxy_path, api_key):
    """Get all users from Hiddify panel"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/user/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        elif e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        raise e

def get_user(proxy_path, api_key, uuid):
    """Get a specific user by UUID"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/user/{uuid}/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 404:
            return None
        elif e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        raise e

def create_user(proxy_path, api_key, user_data):
    """Create a new user in Hiddify panel"""
    headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
    try:
        response = requests.post(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/user/",
            headers=headers,
            json=user_data
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 422:
            error_detail = e.response.json().get("detail", {})
            raise ValueError(f"خطای اعتبارسنجی: {error_detail}")
        elif e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def update_user(proxy_path, api_key, uuid, user_data):
    """Update an existing user"""
    headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
    try:
        response = requests.patch(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/user/{uuid}/",
            headers=headers,
            json=user_data
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"کاربر با UUID {uuid} یافت نشد")
        elif e.response.status_code == 422:
            error_detail = e.response.json().get("detail", {})
            raise ValueError(f"خطای اعتبارسنجی: {error_detail}")
        elif e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        raise e

def delete_user(proxy_path, api_key, uuid):
    """Delete a user by UUID"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.delete(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/user/{uuid}/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"کاربر با UUID {uuid} یافت نشد")
        elif e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        raise e

def get_server_status(proxy_path, api_key):
    """Get server status information"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/server_status/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def get_user_configs(proxy_path, api_key, uuid):
    """Get user configs by UUID"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        # First try with the user's UUID in the path
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/{uuid}/api/v2/user/all-configs/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        # If that fails, try with the API key
        if e.response.status_code == 404:
            try:
                response = requests.get(
                    f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/user/all-configs/",
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except:
                pass
        elif e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        raise e

def update_user_usage(proxy_path, api_key):
    """Update user usage statistics"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/update_user_usage/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def get_user_profile(proxy_path, api_key, uuid=None):
    """Get user profile information"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        if uuid:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/{uuid}/api/v2/user/me/",
                headers=headers
            )
        else:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/user/me/",
                headers=headers
            )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def get_panel_info(proxy_path, api_key):
    """Get panel information"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/panel/info/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def ping_panel(proxy_path, api_key):
    """Ping the panel to check connectivity"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/panel/ping/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def add_user(proxy_path: str, api_key: str, user_data: dict) -> dict:
    """
    Add a new user to the Hiddify panel
    
    Args:
        proxy_path (str): The proxy path from the panel URL
        api_key (str): The API key from the panel URL
        user_data (dict): Dictionary containing user data:
            - name (str): User's name
            - usage_limit_GB (float): Usage limit in GB
            - package_days (int): Number of days for the package
            - comment (str, optional): User comment
            - start_date (str, optional): Start date in YYYY-MM-DD format
    
    Returns:
        dict: The created user's data
    """
    try:
        # Prepare the request data
        data = {
            "name": user_data["name"],
            "usage_limit_GB": user_data["usage_limit_GB"],
            "package_days": user_data["package_days"],
            "comment": user_data.get("comment", ""),
            "start_date": user_data.get("start_date", datetime.now().strftime("%Y-%m-%d")),
            # اضافه کردن مقدارهای پیش‌فرض برای فیلدهای ضروری
            "enable": user_data.get("enable", True),
            "is_active": user_data.get("is_active", True),
            "mode": user_data.get("mode", "monthly")
        }
        
        # Make the API request
        headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
        response = requests.post(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/user/",
            headers=headers,
            json=data
        )
        
        # Check response status
        if response.status_code == 201 or response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("خطای احراز هویت! کلید API نامعتبر است.")
        elif response.status_code == 400 or response.status_code == 422:
            error_content = response.text
            try:
                error_json = response.json()
                if 'detail' in error_json:
                    error_content = error_json['detail']
                    # بررسی ساختار جزئیات خطا برای validation error
                    if isinstance(error_content, dict):
                        validation_errors = []
                        for field, errors in error_content.items():
                            validation_errors.append(f"{field}: {', '.join(errors)}")
                        error_content = " | ".join(validation_errors)
            except:
                pass
            raise Exception(f"خطای اعتبارسنجی داده‌ها: {error_content}")
        else:
            raise Exception(f"خطای ناشناخته با کد {response.status_code}: {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"خطا در اتصال به پنل: {str(e)}")
    except Exception as e:
        raise Exception(f"خطا در افزودن کاربر: {str(e)}")

# توابع جدید برای پشتیبانی از ویژگی‌های API جدید

def get_user_apps(proxy_path, api_key, uuid=None, platform="auto"):
    """Get available apps for user"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        if uuid:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/{uuid}/api/v2/user/apps/?platform={platform}",
                headers=headers
            )
        else:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/user/apps/?platform={platform}",
                headers=headers
            )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def get_mtproxies(proxy_path, api_key, uuid=None):
    """Get MTProxies for user"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        if uuid:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/{uuid}/api/v2/user/mtproxies/",
                headers=headers
            )
        else:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/user/mtproxies/",
                headers=headers
            )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def get_short_link(proxy_path, api_key, uuid=None):
    """Get short link for user configs"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        if uuid:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/{uuid}/api/v2/user/short/",
                headers=headers
            )
        else:
            response = requests.get(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/user/short/",
                headers=headers
            )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def update_user_info(proxy_path, api_key, uuid=None, user_info=None):
    """Update user information like language and telegram_id"""
    headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
    try:
        if uuid:
            response = requests.patch(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/{uuid}/api/v2/user/me/",
                headers=headers,
                json=user_info
            )
        else:
            response = requests.patch(
                f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/user/me/",
                headers=headers,
                json=user_info
            )
        response.raise_for_status()
        return response.json() if response.content else {"status": "success"}
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        elif e.response.status_code == 422:
            error_detail = e.response.json().get("detail", {})
            raise ValueError(f"خطای اعتبارسنجی: {error_detail}")
        raise e

def get_admin_info(proxy_path, api_key):
    """Get current admin information"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/me/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e

def get_all_configs(proxy_path, api_key):
    """Get all panel configurations"""
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(
            f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/all-configs/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPError("خطای احراز هویت! کلید API نامعتبر است.")
        elif e.response.status_code == 404:
            raise HTTPError("مسیر API یافت نشد! لطفا URL پنل را بررسی کنید.")
        raise e
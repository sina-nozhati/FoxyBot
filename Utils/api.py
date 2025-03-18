import requests
import json
import os
from requests.exceptions import HTTPError
from urllib.parse import urlparse
from datetime import datetime
from termcolor import colored

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
    # Check if URL is empty
    if not url:
        raise ValueError("Panel URL cannot be empty")
    
    # Print the URL for debugging
    print(colored(f"Parsing URL: '{url}'", "cyan"))
    
    # Remove trailing and leading whitespace and slashes
    url = url.strip().rstrip("/")
    
    # Parse URL
    try:
        parsed_url = urlparse(url)
        
        # Print parsed components for debugging
        print(colored(f"Parsed URL components:", "cyan"))
        print(colored(f"  Scheme: '{parsed_url.scheme}'", "cyan"))
        print(colored(f"  Netloc: '{parsed_url.netloc}'", "cyan"))
        print(colored(f"  Path: '{parsed_url.path}'", "cyan"))
        
        # Check if URL has scheme and netloc
        if not parsed_url.scheme or not parsed_url.netloc:
            # Try to add scheme if missing
            if not parsed_url.scheme and parsed_url.netloc:
                url = "https://" + url
                parsed_url = urlparse(url)
                print(colored(f"Added https:// scheme: {url}", "yellow"))
            else:
                raise ValueError(f"Invalid panel URL format. URL must include scheme (http/https) and domain. Got scheme='{parsed_url.scheme}', netloc='{parsed_url.netloc}'")
        
        # Extract path parts (removing empty strings)
        path_parts = [part for part in parsed_url.path.split("/") if part]
        
        # Debug information
        print(colored(f"URL: {url}", "yellow"))
        print(colored(f"Path parts: {path_parts}", "yellow"))
        
        # Path should have at least 2 parts
        if len(path_parts) >= 2:
            proxy_path = path_parts[0]  # 7frgemkvtE0
            api_key = path_parts[1]     # 78854985-68dp-425c-989b-7ap0c6kr9bd4
            return proxy_path, api_key
        elif len(path_parts) == 1 and path_parts[0]:
            # If only one part in path, try to use it as proxy_path and ask for api_key
            proxy_path = path_parts[0]
            print(colored(f"Only one path component found: {proxy_path}", "yellow"))
            print(colored("Please manually enter API key:", "yellow"))
            api_key = input("[+] Enter API key: ")
            if not api_key:
                raise ValueError("API key cannot be empty")
            return proxy_path, api_key
        else:
            raise ValueError(f"Invalid panel URL format. Path should have at least 2 parts. Got path='{parsed_url.path}', parts={path_parts}")
    except Exception as e:
        # Useful debugging information
        print(colored(f"Error parsing URL: {url}", "red"))
        print(colored(f"Error details: {str(e)}", "red"))
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Invalid panel URL format. Expected format: https://panel.example.com/proxy_path/api_key. Error: {str(e)}")

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
    """Ping panel to check if it's online"""
    url = f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/panel/ping/"
    headers = {"Hiddify-API-Key": api_key}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def select(url=None):
    """
    Get list of users from panel API, using full URL
    This is a wrapper function for get_users that accepts a full URL
    """
    print(f"Making API call to get users with URL: {url}")
    
    try:
        if not url:
            return []
            
        # Remove trailing slash if present
        url = url.rstrip('/')
        
        # استخراج proxy_path و api_key از URL پنل
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        path_parts = [part for part in parsed_url.path.split("/") if part]
        
        # قسمت مربوط به API را جدا می‌کنیم
        api_path = None
        if '/api/v2' in url:
            # اگر URL حاوی api/v2 باشد، مسیر API را جدا می‌کنیم
            api_index = path_parts.index('api')
            api_path = '/'.join(path_parts[api_index:])
            proxy_path = path_parts[0] if len(path_parts) > 0 else None
        else:
            # در غیر این صورت فرض می‌کنیم اولین بخش مسیر، proxy_path است
            proxy_path = path_parts[0] if len(path_parts) > 0 else None
            api_path = 'api/v2/admin/user'
        
        # ساختن URL نهایی برای درخواست
        final_url = f"{base_url}/{proxy_path}/{api_path}"
        print(f"Final URL for API call: {final_url}")
        
        # پیدا کردن api_key برای استفاده در هدر
        if len(path_parts) >= 2:
            api_key = path_parts[1]
            headers = {"Hiddify-API-Key": api_key}
            
            # ارسال درخواست با هدر مناسب
            response = requests.get(final_url, headers=headers)
            response.raise_for_status()
            
            # پردازش پاسخ
            data = response.json()
            if 'users' in data:
                return data['users']
            else:
                return data
        else:
            print("API key not found in URL path")
            return []
    except Exception as e:
        print(f"Error in select API call: {str(e)}")
        return []

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
    """Get all configs from panel"""
    url = f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/configs"
    headers = {"Hiddify-API-Key": api_key}
    response = requests.get(url, headers=headers)
    try:
        response.raise_for_status()
        return response.json()
    except HTTPError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
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
    """Get user configs by UUID using the original method"""
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
        if e.response.status_code == 404 or e.response.status_code == 401:
            # Get user information from admin API first
            try:
                user_response = requests.get(
                    f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/admin/user/{uuid}/",
                    headers=headers
                )
                user_response.raise_for_status()
                user_data = user_response.json()
                
                # Now try to get configs with secret_uuid (if it's different from uuid)
                secret_uuid = user_data.get("secret_uuid", uuid)
                if secret_uuid != uuid:
                    response = requests.get(
                        f"{HIDDIFY_PANEL_URL}/{proxy_path}/{secret_uuid}/api/v2/user/all-configs/",
                        headers=headers
                    )
                    response.raise_for_status()
                    return response.json()
                
                # If that fails or secret_uuid is the same, try the original URL again
                response = requests.get(
                    f"{HIDDIFY_PANEL_URL}/{proxy_path}/api/v2/user/all-configs/",
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as inner_e:
                # Log the error and re-raise the original exception
                print(f"Error getting user info or configs: {str(inner_e)}")
                raise e
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
        
        # طبق سند API هیدیفای، مسیر صحیح برای دریافت لیست کاربران
        if len(path_parts) >= 2:
            proxy_path = path_parts[0]
            api_key = path_parts[1]
            
            # ساختن URL نهایی برای درخواست API - مسیر دقیق طبق سند API
            final_url = f"{base_url}/{proxy_path}/api/v2/admin/user/"
            print(f"Final URL for API call: {final_url}")
            
            # ارسال درخواست با هدر Hiddify-API-Key که در سند API مشخص شده
            headers = {"Hiddify-API-Key": api_key}
            print(f"Using headers: {headers}")
            
            response = requests.get(final_url, headers=headers)
            print(f"API Response status: {response.status_code}")
            
            # اگر پاسخ موفقیت‌آمیز بود
            if response.status_code == 200:
                try:
                    # سعی می‌کنیم پاسخ JSON را پارس کنیم
                    data = response.json()
                    print(f"API Response data structure: {type(data)}")
                    
                    # طبق سند API، پاسخ آرایه‌ای از کاربران است
                    # {'users': [...]} نیست بلکه خود آرایه است
                    if isinstance(data, list):
                        print(f"Number of users found: {len(data)}")
                        return data
                    else:
                        print(f"Unexpected response format: {data}")
                        return []
                except Exception as e:
                    print(f"Error parsing JSON response: {str(e)}")
                    print(f"Response content: {response.text[:200]}...")
                    return []
            else:
                print(f"API request failed with status code: {response.status_code}")
                print(f"Response content: {response.text[:200]}...")
                return []
        else:
            print("Invalid URL path, couldn't extract proxy_path and api_key")
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

# Add legacy alias functions for backward compatibility
# معادل‌سازی توابع قدیمی با توابع جدید برای حفظ سازگاری با کد قبلی
def insert(url, name, package_days, usage_limit_GB, comment=None, enable=True, is_active=True, mode="monthly"):
    """
    Legacy wrapper for add_user function used in bot.py
    """
    print(f"Legacy insert called: {name}, {package_days} days, {usage_limit_GB} GB")
    
    # استخراج proxy_path و api_key از URL پنل
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    path_parts = [part for part in parsed_url.path.split("/") if part]
    
    if len(path_parts) < 2:
        print(f"Invalid URL format: {url}")
        return False
        
    proxy_path = path_parts[0]
    api_key = path_parts[1]
    
    # تنظیم URL پایه
    global HIDDIFY_PANEL_URL
    old_url = HIDDIFY_PANEL_URL
    HIDDIFY_PANEL_URL = base_url
    
    try:
        user_data = {
            "name": name,
            "package_days": package_days,
            "usage_limit_GB": usage_limit_GB,
            "comment": comment or "",
            "enable": enable,
            "is_active": is_active,
            "mode": mode
        }
        
        # فراخوانی تابع اصلی
        result = add_user(proxy_path, api_key, user_data)
        
        # بازگرداندن UUID کاربر ایجاد شده
        if result and "uuid" in result:
            print(f"User created successfully with UUID: {result['uuid']}")
            return result["uuid"]
        else:
            print("Failed to create user: No UUID in response")
            return False
    except Exception as e:
        print(f"Error inserting user: {str(e)}")
        return False
    finally:
        # بازگرداندن URL قبلی
        HIDDIFY_PANEL_URL = old_url


def update(url, uuid, **kwargs):
    """
    Legacy wrapper for update_user function used in bot.py
    """
    print(f"Legacy update called for UUID {uuid}, params: {kwargs}")
    
    # استخراج proxy_path و api_key از URL پنل
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    path_parts = [part for part in parsed_url.path.split("/") if part]
    
    if len(path_parts) < 2:
        print(f"Invalid URL format: {url}")
        return False
        
    proxy_path = path_parts[0]
    api_key = path_parts[1]
    
    # تنظیم URL پایه
    global HIDDIFY_PANEL_URL
    old_url = HIDDIFY_PANEL_URL
    HIDDIFY_PANEL_URL = base_url
    
    try:
        # فراخوانی تابع اصلی
        result = update_user(proxy_path, api_key, uuid, kwargs)
        return result
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return False
    finally:
        # بازگرداندن URL قبلی
        HIDDIFY_PANEL_URL = old_url


def find(url, uuid):
    """
    Legacy wrapper for get_user function used in bot.py
    """
    print(f"Legacy find called for UUID {uuid}")
    
    # استخراج proxy_path و api_key از URL پنل
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    path_parts = [part for part in parsed_url.path.split("/") if part]
    
    if len(path_parts) < 2:
        print(f"Invalid URL format: {url}")
        return False
        
    proxy_path = path_parts[0]
    api_key = path_parts[1]
    
    # تنظیم URL پایه
    global HIDDIFY_PANEL_URL
    old_url = HIDDIFY_PANEL_URL
    HIDDIFY_PANEL_URL = base_url
    
    try:
        # فراخوانی تابع اصلی
        result = get_user(proxy_path, api_key, uuid)
        return result
    except Exception as e:
        print(f"Error finding user: {str(e)}")
        return False
    finally:
        # بازگرداندن URL قبلی
        HIDDIFY_PANEL_URL = old_url

def get_user_proxy_path(hiddify_panel_url: str, admin_proxy_path: str, api_key: str, user_uuid: str) -> str:
    """
    دریافت مسیر پروکسی کاربر از طریق API
    
    Args:
        hiddify_panel_url: آدرس پنل هیدیفای
        admin_proxy_path: مسیر پروکسی ادمین
        api_key: کلید API
        user_uuid: شناسه یکتای کاربر
        
    Returns:
        str: مسیر پروکسی کاربر
    """
    try:
        # دریافت اطلاعات کاربر از طریق API ادمین
        response = requests.get(
            f"{hiddify_panel_url}/{admin_proxy_path}/api/v2/admin/user/{user_uuid}/",
            headers={"Hiddify-API-Key": api_key}
        )
        response.raise_for_status()
        user_data = response.json()
        
        # سعی می‌کنیم بررسی کنیم آیا در پاسخ API فیلدهای دیگری برای مسیر پروکسی وجود دارد
        print(f"User data keys: {list(user_data.keys())}")
        
        # بررسی فیلدهای احتمالی که ممکن است حاوی مسیر پروکسی باشند
        if "proxy_path" in user_data and user_data["proxy_path"]:
            print(f"Found proxy_path: {user_data['proxy_path']}")
            return user_data["proxy_path"]
        elif "secret_uuid" in user_data:
            # اگر secret_uuid با uuid متفاوت باشد، از آن استفاده می‌کنیم
            secret_uuid = user_data["secret_uuid"]
            if secret_uuid != user_uuid:
                return secret_uuid
        
        # اگر هیچ کدام از موارد بالا یافت نشد، از UUID ورودی استفاده می‌کنیم
        return user_uuid
            
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت مسیر پروکسی کاربر: {str(e)}")
        raise

def get_user_configs(hiddify_panel_url: str, admin_proxy_path: str, api_key: str, user_uuid: str) -> dict:
    """
    دریافت کانفیگ‌های کاربر با استفاده از UUID
    
    Args:
        hiddify_panel_url: آدرس پنل هیدیفای
        admin_proxy_path: مسیر پروکسی ادمین
        api_key: کلید API
        user_uuid: شناسه یکتای کاربر
        
    Returns:
        dict: کانفیگ‌های کاربر
    """
    try:
        # ابتدا اطلاعات کاربر را دریافت می‌کنیم
        user_response = requests.get(
            f"{hiddify_panel_url}/{admin_proxy_path}/api/v2/admin/user/{user_uuid}/",
            headers={"Hiddify-API-Key": api_key}
        )
        user_response.raise_for_status()
        user_data = user_response.json()
        
        # اگر secret_uuid وجود داشته باشد و متفاوت از uuid ورودی باشد، از آن استفاده می‌کنیم
        secret_uuid = user_data.get("secret_uuid", user_uuid)
        
        # تلاش برای دریافت کانفیگ‌ها با secret_uuid
        try:
            response = requests.get(
                f"{hiddify_panel_url}/{admin_proxy_path}/{secret_uuid}/api/v2/user/all-configs/",
                headers={"Hiddify-API-Key": api_key}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            # اگر روش اول موفق نبود، تلاش می‌کنیم با استفاده از مسیر پروکسی کاربر
            user_proxy_path = get_user_proxy_path(hiddify_panel_url, admin_proxy_path, api_key, user_uuid)
            
            response = requests.get(
                f"{hiddify_panel_url}/{user_proxy_path}/api/v2/user/all-configs/",
                headers={"Hiddify-API-Key": api_key}
            )
            response.raise_for_status()
            return response.json()
            
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت کانفیگ‌های کاربر: {str(e)}")
        raise
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config import HIDDIFY_API_VERSION, HIDDIFY_API_BASE_URL

class HiddifyAPI:
    def __init__(self, domain: str, proxy_path: str, api_key: str):
        self.domain = domain
        self.proxy_path = proxy_path
        self.api_key = api_key
        self.base_url = f"{HIDDIFY_API_BASE_URL}/{proxy_path}/api/{HIDDIFY_API_VERSION}"
        self.headers = {"Hiddify-API-Key": api_key}

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def get_server_status(self) -> Dict:
        """دریافت وضعیت سرور"""
        return self._make_request("GET", "admin/server_status/")

    def get_all_users(self) -> List[Dict]:
        """دریافت لیست تمام کاربران"""
        return self._make_request("GET", "admin/user/")

    def create_user(self, user_data: Dict) -> Dict:
        """ایجاد کاربر جدید"""
        return self._make_request("POST", "admin/user/", json=user_data)

    def get_user(self, uuid: str) -> Dict:
        """دریافت اطلاعات یک کاربر"""
        return self._make_request("GET", f"admin/user/{uuid}/")

    def update_user(self, uuid: str, user_data: Dict) -> Dict:
        """بروزرسانی اطلاعات کاربر"""
        return self._make_request("PATCH", f"admin/user/{uuid}/", json=user_data)

    def delete_user(self, uuid: str) -> Dict:
        """حذف کاربر"""
        return self._make_request("DELETE", f"admin/user/{uuid}/")

    def get_user_configs(self, uuid: str) -> List[Dict]:
        """دریافت تنظیمات کاربر"""
        return self._make_request("GET", f"user/all-configs/")

    def get_user_profile(self, uuid: str) -> Dict:
        """دریافت پروفایل کاربر"""
        return self._make_request("GET", f"user/me/")

    def get_user_apps(self, platform: str = "auto") -> List[Dict]:
        """دریافت لیست اپلیکیشن‌های کاربر"""
        return self._make_request("GET", "user/apps/", params={"platform": platform})

    def get_user_mtproxies(self) -> List[Dict]:
        """دریافت لیست پروکسی‌های MTProto"""
        return self._make_request("GET", "user/mtproxies/")

    def get_user_short_url(self) -> Dict:
        """دریافت لینک کوتاه کاربر"""
        return self._make_request("GET", "user/short/")

    def create_subscription(self, user_data: Dict) -> Dict:
        """ایجاد اشتراک جدید"""
        # تنظیم تاریخ شروع و پایان
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=user_data["duration_days"])
        
        # تنظیم محدودیت ترافیک
        user_data.update({
            "start_date": start_date.strftime("%Y-%m-%d"),
            "usage_limit_GB": user_data["traffic_gb"],
            "enable": True,
            "is_active": True
        })
        
        return self.create_user(user_data)

    def update_subscription(self, uuid: str, user_data: Dict) -> Dict:
        """بروزرسانی اشتراک"""
        return self.update_user(uuid, user_data)

    def get_subscription_status(self, uuid: str) -> Dict:
        """دریافت وضعیت اشتراک"""
        profile = self.get_user_profile(uuid)
        return {
            "is_active": profile.get("is_active", False),
            "traffic_used": profile.get("profile_usage_current", 0),
            "traffic_total": profile.get("profile_usage_total", 0),
            "remaining_days": profile.get("profile_remaining_days", 0),
            "reset_days": profile.get("profile_reset_days", 0)
        }

    def check_panel_status(self) -> bool:
        """بررسی وضعیت پنل"""
        try:
            response = self._make_request("GET", "panel/ping/")
            return response.get("msg") == "pong"
        except:
            return False
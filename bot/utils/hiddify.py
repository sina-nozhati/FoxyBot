import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config import HIDDIFY_API_VERSION, HIDDIFY_API_BASE_URL, HIDDIFY_USER_PROXY_PATH

class HiddifyAPI:
    def __init__(self, domain: str, proxy_path: str, api_key: str, user_proxy_path: Optional[str] = None):
        """
        Initialize the Hiddify API client.
        
        Args:
            domain: Domain of the Hiddify panel
            proxy_path: Admin proxy path for the API
            api_key: API key for authentication
            user_proxy_path: User proxy path for accessing user configurations
        """
        self.domain = domain
        self.proxy_path = proxy_path  # Admin proxy path
        self.user_proxy_path = user_proxy_path or HIDDIFY_USER_PROXY_PATH  # User proxy path
        self.api_key = api_key
        
        # Construct base URL correctly based on domain format
        if '://' in domain:  # If domain already includes protocol
            self.base_url = f"{domain}/{proxy_path}/api/{HIDDIFY_API_VERSION}"
        else:
            self.base_url = f"https://{domain}/{proxy_path}/api/{HIDDIFY_API_VERSION}"
            
        self.headers = {"Hiddify-API-Key": api_key}

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make an API request to the Hiddify panel"""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()
        
    def _get_user_url(self, uuid: str = None) -> str:
        """
        Generate the user-specific URL for accessing configurations
        
        Args:
            uuid: The user UUID
            
        Returns:
            Properly formatted user URL
        """
        if '://' in self.domain:
            base = f"{self.domain}/{self.user_proxy_path}"
        else:
            base = f"https://{self.domain}/{self.user_proxy_path}"
            
        if uuid:
            return f"{base}/{uuid}"
        return base

    def get_server_status(self) -> Dict:
        """Get server status"""
        return self._make_request("GET", "admin/server_status/")

    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        return self._make_request("GET", "admin/user/")

    def create_user(self, user_data: Dict) -> Dict:
        """Create a new user"""
        return self._make_request("POST", "admin/user/", json=user_data)

    def get_user(self, uuid: str) -> Dict:
        """Get user information"""
        return self._make_request("GET", f"admin/user/{uuid}/")

    def update_user(self, uuid: str, user_data: Dict) -> Dict:
        """Update user information"""
        return self._make_request("PATCH", f"admin/user/{uuid}/", json=user_data)

    def delete_user(self, uuid: str) -> Dict:
        """Delete a user"""
        return self._make_request("DELETE", f"admin/user/{uuid}/")

    def get_user_configs(self, uuid: str) -> List[Dict]:
        """
        Get user configurations using user proxy path
        
        Args:
            uuid: The user UUID
            
        Returns:
            List of configurations for the user
        """
        # Using custom request to user proxy path
        user_url = f"{self._get_user_url(uuid)}/all-configs/"
        response = requests.get(user_url)
        response.raise_for_status()
        return response.json()

    def get_user_profile(self, uuid: str) -> Dict:
        """
        Get user profile using user proxy path
        
        Args:
            uuid: The user UUID
            
        Returns:
            User profile information
        """
        user_url = f"{self._get_user_url(uuid)}/me/"
        response = requests.get(user_url)
        response.raise_for_status()
        return response.json()

    def get_user_apps(self, uuid: str, platform: str = "auto") -> List[Dict]:
        """
        Get user applications using user proxy path
        
        Args:
            uuid: The user UUID
            platform: Target platform (auto, android, ios, etc.)
            
        Returns:
            List of applications for the user
        """
        user_url = f"{self._get_user_url(uuid)}/apps/"
        response = requests.get(user_url, params={"platform": platform})
        response.raise_for_status()
        return response.json()

    def get_user_mtproxies(self, uuid: str) -> List[Dict]:
        """
        Get MTProto proxies using user proxy path
        
        Args:
            uuid: The user UUID
            
        Returns:
            List of MTProto proxies for the user
        """
        user_url = f"{self._get_user_url(uuid)}/mtproxies/"
        response = requests.get(user_url)
        response.raise_for_status()
        return response.json()

    def get_user_short_url(self, uuid: str) -> Dict:
        """
        Get short URL for user using user proxy path
        
        Args:
            uuid: The user UUID
            
        Returns:
            Short URL information for the user
        """
        user_url = f"{self._get_user_url(uuid)}/short/"
        response = requests.get(user_url)
        response.raise_for_status()
        return response.json()

    def create_subscription(self, user_data: Dict) -> Dict:
        """Create a new subscription"""
        # Set start and end date
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=user_data["duration_days"])
        
        # Set traffic limit
        user_data.update({
            "start_date": start_date.strftime("%Y-%m-%d"),
            "usage_limit_GB": user_data["traffic_gb"],
            "enable": True,
            "is_active": True
        })
        
        return self.create_user(user_data)

    def update_subscription(self, uuid: str, user_data: Dict) -> Dict:
        """Update subscription"""
        return self.update_user(uuid, user_data)

    def get_subscription_status(self, uuid: str) -> Dict:
        """Get subscription status"""
        profile = self.get_user_profile(uuid)
        return {
            "is_active": profile.get("is_active", False),
            "traffic_used": profile.get("profile_usage_current", 0),
            "traffic_total": profile.get("profile_usage_total", 0),
            "remaining_days": profile.get("profile_remaining_days", 0),
            "reset_days": profile.get("profile_reset_days", 0)
        }

    def check_panel_status(self) -> bool:
        """Check panel status"""
        try:
            response = self._make_request("GET", "panel/ping/")
            if 'msg' in response and ('PONG' in response.get('msg', '') or 'pong' in response.get('msg', '')):
                return True
            return False
        except Exception as e:
            print(f"Error checking panel status: {e}")
            return False
            
    def get_user_dashboard_url(self, uuid: str) -> str:
        """
        Generate the user dashboard URL
        
        Args:
            uuid: The user UUID
            
        Returns:
            Complete URL to user dashboard
        """
        return self._get_user_url(uuid)

    def check_user_panel_access(self, uuid: str) -> bool:
        """
        Check if user panel is accessible with the given UUID
        
        Args:
            uuid: User UUID to test
            
        Returns:
            True if access is successful, False otherwise
        """
        try:
            user_url = f"{self._get_user_url(uuid)}/api/v2/user/me/"
            response = requests.get(user_url)
            
            if response.status_code == 200:
                # بررسی اینکه آیا پاسخ دارای عنوان پروفایل می‌باشد
                user_data = response.json()
                if 'profile_title' in user_data:
                    print(f"User profile title: {user_data['profile_title']}")
                    return True
                else:
                    print("User profile title not found in response")
                    return False
            return False
        except Exception as e:
            print(f"Error checking user panel access: {e}")
            return False
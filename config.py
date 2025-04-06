import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot settings
ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
USER_BOT_TOKEN = os.getenv('USER_BOT_TOKEN')

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/foxybot')

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'your-encryption-key-here')

# Hiddify panel settings
HIDDIFY_API_VERSION = os.getenv('HIDDIFY_API_VERSION', 'v2')
HIDDIFY_API_BASE_URL = os.getenv('HIDDIFY_API_BASE_URL', 'https://panel.hiddify.com')
HIDDIFY_PROXY_PATH = os.getenv('HIDDIFY_PROXY_PATH', 'proxy')  # Admin proxy path
HIDDIFY_USER_PROXY_PATH = os.getenv('HIDDIFY_USER_PROXY_PATH', 'proxy')  # User proxy path
HIDDIFY_API_KEY = os.getenv('HIDDIFY_API_KEY', 'your-api-key-here')

# Payment settings
PAYMENT_CARD_NUMBER = os.getenv('PAYMENT_CARD_NUMBER', '6037-XXXX-XXXX-1234')

# Notification settings
TRAFFIC_ALERT_THRESHOLD = 0.85  # 85% traffic usage
EXPIRY_ALERT_DAYS = [3, 1]  # Days before expiry to send alert

# Default plan settings
DEFAULT_PLANS = [
    {
        'name': '🔥 1 Month',
        'duration_days': 30,
        'traffic_gb': 30,
        'price': 20000,
        'description': '1 month plan with 30 GB traffic'
    },
    {
        'name': '💎 3 Months',
        'duration_days': 90,
        'traffic_gb': 100,
        'price': 50000,
        'description': '3 months plan with 100 GB traffic'
    },
    {
        'name': '🎁 Free Trial',
        'duration_days': 3,
        'traffic_gb': 5,
        'price': 0,
        'description': '3 days trial with 5 GB traffic'
    }
]

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'logs/foxybot.log'

# Cron job settings
CRON_UPDATE_INTERVAL = '*/5 * * * *'  # Every 5 minutes
CRON_BACKUP_INTERVAL = '0 0 * * *'    # Every day at 00:00 
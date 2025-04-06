#!/usr/bin/env python3
import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        logger.error("❌ .env file not found!")
        return False
    
    load_dotenv()
    required_vars = [
        'ADMIN_BOT_TOKEN', 
        'USER_BOT_TOKEN',
        'HIDDIFY_API_BASE_URL',
        'HIDDIFY_PROXY_PATH',
        'HIDDIFY_USER_PROXY_PATH',
        'HIDDIFY_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def check_telegram_bot(token, bot_type):
    """Check if Telegram bot token is valid"""
    logger.info(f"🔍 Validating {bot_type} Telegram bot...")
    
    response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
    if response.status_code != 200:
        logger.error(f"❌ Invalid {bot_type} bot token: {response.text}")
        return False
    
    data = response.json()
    if not data.get('ok'):
        logger.error(f"❌ Invalid {bot_type} bot token: {data.get('description')}")
        return False
    
    logger.info(f"✅ {bot_type} bot validated: @{data['result']['username']} ({data['result']['first_name']})")
    return True

def check_hiddify_panel():
    """Check if Hiddify panel is accessible"""
    logger.info("🔍 Validating Hiddify admin panel access...")
    
    base_url = os.getenv('HIDDIFY_API_BASE_URL')
    admin_proxy_path = os.getenv('HIDDIFY_PROXY_PATH')
    user_proxy_path = os.getenv('HIDDIFY_USER_PROXY_PATH')
    api_key = os.getenv('HIDDIFY_API_KEY')
    
    # Domain might include protocol
    if '://' in base_url:
        domain = base_url.split('://')[1]
    else:
        domain = base_url
        base_url = f"https://{base_url}"
    
    # Check admin panel using ping endpoint
    ping_url = f"{base_url}/{admin_proxy_path}/api/v2/panel/ping/"
    try:
        response = requests.get(
            ping_url,
            headers={"Hiddify-API-Key": api_key},
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to connect to admin panel: HTTP {response.status_code}")
            return False
        
        data = response.json()
        logger.info(f"✅ Admin panel responded with: {data}")
        
        # Check if response contains 'msg' with 'PONG' or 'pong'
        if 'msg' in data and ('PONG' in data['msg'] or 'pong' in data['msg']):
            logger.info(f"✅ Admin panel connection validated successfully!")
            
            # Check if we can get users list (admin functionality)
            users_url = f"{base_url}/{admin_proxy_path}/api/v2/admin/user/"
            users_response = requests.get(
                users_url,
                headers={"Hiddify-API-Key": api_key},
                timeout=10
            )
            
            if users_response.status_code != 200:
                logger.warning(f"⚠️ Could not get users list: HTTP {users_response.status_code}")
                return False
            else:
                users = users_response.json()
                users_count = len(users)
                logger.info(f"✅ Successfully retrieved users list ({users_count} users)")
                
                # Validate user proxy path if we have users
                if users_count > 0:
                    logger.info("🔍 Validating user proxy path...")
                    
                    # Find a user (prefer one named 'default' if exists)
                    target_user = None
                    for user in users:
                        if user.get('name', '').lower() == 'default':
                            target_user = user
                            break
                    
                    # If no 'default' user found, use the first one
                    if not target_user and users:
                        target_user = users[0]
                    
                    if target_user and 'uuid' in target_user:
                        user_uuid = target_user.get('uuid')
                        user_name = target_user.get('name')
                        logger.info(f"✅ Using user: {user_name} (UUID: {user_uuid})")
                        
                        # Try to access user profile URL
                        user_url = f"{base_url}/{user_proxy_path}/{user_uuid}/api/v2/user/me/"
                        try:
                            user_response = requests.get(user_url, timeout=10)
                            if user_response.status_code == 200:
                                # بررسی اطلاعات پروفایل کاربر
                                user_data = user_response.json()
                                if 'profile_title' in user_data:
                                    profile_title = user_data.get('profile_title', '')
                                    logger.info(f"✅ User profile title: {profile_title}")
                                    logger.info(f"✅ User proxy path validated successfully")
                                    return True
                                else:
                                    logger.warning("⚠️ User profile title not found in response")
                                    logger.info(f"✅ User proxy path accessible but profile data incomplete")
                                    return True
                            else:
                                logger.error(f"❌ Could not validate user proxy path: HTTP {user_response.status_code}")
                                return False
                        except requests.exceptions.RequestException as e:
                            logger.error(f"❌ Could not validate user proxy path: {str(e)}")
                            return False
                else:
                    logger.warning("⚠️ No users found to validate user proxy path")
                    # Continue anyway since admin panel works
                    return True
            
            return True
        else:
            logger.error(f"❌ Unexpected response from admin panel: {data}")
            return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to connect to panel: {str(e)}")
        return False

def check_database():
    """Check database connection"""
    logger.info("🔍 Validating database connection...")
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL not set")
        return False
    
    try:
        import psycopg2
        
        # Parse database URL
        if '://' in db_url:
            # postgresql://user:password@localhost:5432/dbname
            parts = db_url.split('://', 1)[1].split('@')
            user_pass = parts[0].split(':')
            host_port_db = parts[1].split('/')
            host_port = host_port_db[0].split(':')
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ''
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else '5432'
            dbname = host_port_db[1]
            
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )
            conn.close()
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.error("❌ Invalid DATABASE_URL format")
            return False
    except ImportError:
        logger.error("❌ psycopg2 module not installed")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {str(e)}")
        return False

def main():
    """Main function to check all connections"""
    logger.info("🚀 Starting connection tests...")
    
    # Check environment
    if not check_environment():
        return False
    
    # Check Telegram bots
    admin_bot_ok = check_telegram_bot(os.getenv('ADMIN_BOT_TOKEN'), 'Admin')
    user_bot_ok = check_telegram_bot(os.getenv('USER_BOT_TOKEN'), 'User')
    
    # Check Hiddify panel
    panel_ok = check_hiddify_panel()
    
    # Check database
    db_ok = check_database()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("📊 Connection Test Summary:")
    logger.info(f"Admin Bot: {'✅ OK' if admin_bot_ok else '❌ Failed'}")
    logger.info(f"User Bot: {'✅ OK' if user_bot_ok else '❌ Failed'}")
    logger.info(f"Hiddify Panel: {'✅ OK' if panel_ok else '❌ Failed'}")
    logger.info(f"Database: {'✅ OK' if db_ok else '❌ Failed'}")
    logger.info("="*50)
    
    if admin_bot_ok and user_bot_ok and panel_ok and db_ok:
        logger.info("✅ All connections successful! System ready to start.")
        return True
    else:
        logger.error("❌ Some connections failed. Please fix the issues before starting the system.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
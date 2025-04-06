#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
import requests
from datetime import datetime

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def send_telegram_message(bot_token, chat_id, message, parse_mode="HTML"):
    """Send a message to a Telegram chat using the Bot API."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False

def load_env_file(env_path):
    """Load environment variables from .env file."""
    env_vars = {}
    try:
        with open(env_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                env_vars[key] = value.strip('"\'')
        return env_vars
    except Exception as e:
        logger.error(f"Failed to load .env file: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Send notification to Telegram admin.')
    parser.add_argument('--message', '-m', default=None, help='Message to send')
    parser.add_argument('--env-file', '-e', default='.env', help='Path to .env file')
    args = parser.parse_args()

    # Load environment variables
    env_vars = load_env_file(args.env_file)
    
    # Get bot token and admin ID
    bot_token = env_vars.get('ADMIN_BOT_TOKEN')
    admin_id = env_vars.get('ADMIN_TELEGRAM_ID')
    
    if not bot_token or not admin_id:
        logger.error("Missing ADMIN_BOT_TOKEN or ADMIN_TELEGRAM_ID in .env file")
        sys.exit(1)
    
    # Default message if none provided
    message = args.message
    if not message:
        hostname = os.popen('hostname').read().strip()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"✅ <b>FoxyVPN Bot</b> was successfully updated on server <code>{hostname}</code> at {current_time}."
    
    # Send notification
    logger.info(f"Sending update notification to admin (ID: {admin_id})")
    if send_telegram_message(bot_token, admin_id, message):
        logger.info("✅ Notification sent successfully")
    else:
        logger.error("❌ Failed to send notification")
        sys.exit(1)

if __name__ == "__main__":
    main() 
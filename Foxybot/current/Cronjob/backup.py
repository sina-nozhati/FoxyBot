import os
import sys
import json
import time
import shutil
import sqlite3
import requests
from datetime import datetime
import zipfile
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import load_config
from Database.dbManager import add_backup, get_setting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backup.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("backup")

def create_backup(backup_type="auto"):
    """Create a backup of the database and configuration"""
    try:
        config = load_config()
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"foxybot_backup_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create zip file
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database file
            db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Database", "hiddify_bot.db")
            if os.path.exists(db_file):
                zipf.write(db_file, os.path.basename(db_file))
            
            # Add config file
            config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
            if os.path.exists(config_file):
                zipf.write(config_file, os.path.basename(config_file))
            
            # Add JSON files from UserBot and AdminBot
            for bot_dir in ["UserBot", "AdminBot"]:
                json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), bot_dir, "Json")
                if os.path.exists(json_dir):
                    for json_file in os.listdir(json_dir):
                        if json_file.endswith(".json"):
                            file_path = os.path.join(json_dir, json_file)
                            zipf.write(file_path, os.path.join(bot_dir, "Json", json_file))
        
        # Get file size
        file_size = os.path.getsize(backup_path)
        
        # Add backup record to database
        backup_id = add_backup(backup_filename, None, file_size, backup_type)
        
        # Upload to cloud if enabled
        if config.get('BACKUP_CLOUD_ENABLED', "0") == "1" and config.get('BACKUP_CLOUD_TOKEN'):
            upload_to_cloud(backup_path, backup_filename, config['BACKUP_CLOUD_TOKEN'])
        
        logger.info(f"Backup created successfully: {backup_filename}")
        return backup_path, backup_filename
    
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return None, None

def upload_to_cloud(file_path, filename, token):
    """Upload backup to cloud storage"""
    try:
        # This is a placeholder for cloud upload functionality
        # You can implement integration with services like Telegram, Google Drive, etc.
        logger.info(f"Uploading backup to cloud: {filename}")
        
        # Example: Upload to a custom API
        # with open(file_path, 'rb') as f:
        #     files = {'file': (filename, f)}
        #     response = requests.post(
        #         'https://your-cloud-storage-api.com/upload',
        #         files=files,
        #         headers={'Authorization': f'Bearer {token}'}
        #     )
        #     if response.status_code == 200:
        #         logger.info(f"Backup uploaded to cloud successfully: {filename}")
        #     else:
        #         logger.error(f"Failed to upload backup to cloud: {response.text}")
        
        logger.info(f"Backup would be uploaded to cloud (placeholder): {filename}")
        return True
    
    except Exception as e:
        logger.error(f"Error uploading backup to cloud: {str(e)}")
        return False

def restore_backup(backup_path):
    """Restore from a backup file"""
    try:
        # Extract backup
        extract_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "restore_temp")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(extract_dir)
        
        # Stop bots if they're running
        # This would need to be implemented based on how you run your bots
        
        # Restore database
        db_file = os.path.join(extract_dir, "hiddify_bot.db")
        if os.path.exists(db_file):
            target_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Database", "hiddify_bot.db")
            shutil.copy2(db_file, target_db)
        
        # Restore config
        config_file = os.path.join(extract_dir, "config.json")
        if os.path.exists(config_file):
            target_config = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
            shutil.copy2(config_file, target_config)
        
        # Restore JSON files
        for bot_dir in ["UserBot", "AdminBot"]:
            json_dir = os.path.join(extract_dir, bot_dir, "Json")
            if os.path.exists(json_dir):
                target_json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), bot_dir, "Json")
                os.makedirs(target_json_dir, exist_ok=True)
                
                for json_file in os.listdir(json_dir):
                    if json_file.endswith(".json"):
                        source_file = os.path.join(json_dir, json_file)
                        target_file = os.path.join(target_json_dir, json_file)
                        shutil.copy2(source_file, target_file)
        
        # Clean up
        shutil.rmtree(extract_dir)
        
        logger.info(f"Backup restored successfully from: {backup_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        return False

def auto_backup():
    """Run automatic backup based on configuration"""
    try:
        config = load_config()
        
        if config.get('BACKUP_ENABLED', "0") != "1":
            logger.info("Automatic backup is disabled")
            return False
        
        # Check last backup time
        last_backup_time = get_setting("last_auto_backup_time")
        if last_backup_time:
            last_backup = datetime.strptime(last_backup_time, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            
            # Calculate hours since last backup
            hours_diff = (now - last_backup).total_seconds() / 3600
            backup_interval = int(config.get('BACKUP_INTERVAL', "24"))
            
            if hours_diff < backup_interval:
                logger.info(f"Skipping auto backup, last backup was {hours_diff:.1f} hours ago (interval: {backup_interval} hours)")
                return False
        
        # Create backup
        backup_path, backup_filename = create_backup("auto")
        
        if backup_path:
            # Update last backup time
            from Database.dbManager import set_setting
            set_setting("last_auto_backup_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            logger.info(f"Auto backup completed successfully: {backup_filename}")
            return True
        else:
            logger.error("Auto backup failed")
            return False
    
    except Exception as e:
        logger.error(f"Error in auto backup: {str(e)}")
        return False

if __name__ == "__main__":
    # If run directly, perform auto backup
    auto_backup()


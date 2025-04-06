#!/bin/bash

# Set colors for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}           FoxyVPN Bot Update Tool              ${NC}"
echo -e "${BLUE}================================================${NC}"

# Installation directory
INSTALL_DIR=${INSTALL_DIR:-"/opt/foxybot"}

# Check if installation directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}❌ Error: Installation directory $INSTALL_DIR not found!${NC}"
    exit 1
fi

# Stop the service
echo -e "${YELLOW}🔄 Stopping the service...${NC}"
systemctl stop foxybot.service

# Navigate to installation directory
cd "$INSTALL_DIR" || exit 1

# Backup current .env file
echo -e "${YELLOW}🔄 Backing up .env file...${NC}"
if [ -f .env ]; then
    cp .env .env.backup
    echo -e "${GREEN}✅ Backup created: .env.backup${NC}"
fi

# Reset any local changes
echo -e "${YELLOW}🔄 Resetting local changes...${NC}"
git reset --hard HEAD

# Update code from Git
echo -e "${YELLOW}🔄 Updating code from GitHub...${NC}"
git pull --force

# Restore .env file
echo -e "${YELLOW}🔄 Restoring .env file...${NC}"
if [ -f .env.backup ]; then
    cp .env.backup .env
    echo -e "${GREEN}✅ .env file restored${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}🔄 Activating virtual environment...${NC}"
source venv/bin/activate

# Update libraries
echo -e "${YELLOW}🔄 Updating dependencies...${NC}"
pip install -r requirements.txt

# Make sure the database is up to date
echo -e "${YELLOW}🔄 Checking database connection...${NC}"
python -c "
import os
import sys
sys.path.insert(0, os.path.abspath(''))
from config import DATABASE_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    session.execute('SELECT 1')
    session.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection error: {e}')
    sys.exit(1)
"

# Make update_notification.py executable
if [ -f bot/utils/send_notification.py ]; then
    chmod +x bot/utils/send_notification.py
fi

# Restart the service
echo -e "${YELLOW}🔄 Restarting the service...${NC}"
systemctl start foxybot.service

# Wait for service to start
echo -e "${YELLOW}🔄 Waiting for service to start...${NC}"
sleep 5

# Check service status
echo -e "${YELLOW}🔄 Checking service status...${NC}"
SERVICE_STATUS=$(systemctl is-active foxybot.service)

if [ "$SERVICE_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ Service is running!${NC}"
    
    # Send notification via Python script
    echo -e "${YELLOW}🔄 Sending notification to admin via Telegram...${NC}"
    
    if [ -f bot/utils/send_notification.py ]; then
        python bot/utils/send_notification.py --message "✅ <b>FoxyVPN Bot</b> was successfully updated on server <code>$(hostname)</code> at $(date). All features are now active."
        echo -e "${GREEN}✅ Update notification sent to admin${NC}"
    else
        echo -e "${YELLOW}⚠️ Could not send notification: send_notification.py not found${NC}"
        
        # Fallback to curl
        if [ -f .env ]; then
            # Load environment variables
            export $(grep -v '^#' .env | xargs)
            
            # Send message using curl
            if [ ! -z "$ADMIN_BOT_TOKEN" ] && [ ! -z "$ADMIN_TELEGRAM_ID" ]; then
                MESSAGE="✅ FoxyVPN Bot was successfully updated on server $(hostname) at $(date)."
                curl -s "https://api.telegram.org/bot$ADMIN_BOT_TOKEN/sendMessage" \
                    -d "chat_id=$ADMIN_TELEGRAM_ID" \
                    -d "text=$MESSAGE" \
                    -d "parse_mode=HTML" > /dev/null
                    
                echo -e "${GREEN}✅ Update notification sent to admin using curl${NC}"
            else
                echo -e "${YELLOW}⚠️ Could not send notification: Missing bot token or admin ID${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️ Could not send notification: .env file not found${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Service failed to start! Status: $SERVICE_STATUS${NC}"
    echo -e "${YELLOW}🔍 Check logs with: journalctl -u foxybot.service -n 50${NC}"
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ FoxyVPN Bot update process completed!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}🔍 To view logs:${NC} journalctl -u foxybot.service -f"
echo -e "${BLUE}================================================${NC}"
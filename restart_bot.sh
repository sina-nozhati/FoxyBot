#!/bin/bash

# Set colors for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}           FoxyVPN Bot Restart Tool             ${NC}"
echo -e "${BLUE}================================================${NC}"

# Installation directory
INSTALL_DIR=${INSTALL_DIR:-"/opt/foxybot"}

# Check if installation directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}❌ Error: Installation directory $INSTALL_DIR not found!${NC}"
    exit 1
fi

# Navigate to installation directory
cd "$INSTALL_DIR" || exit 1

# Stop the service
echo -e "${YELLOW}🔄 Stopping the service...${NC}"
systemctl stop foxybot.service

# Activate virtual environment
echo -e "${YELLOW}🔄 Activating virtual environment...${NC}"
source venv/bin/activate

# Check database connection
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

# Start the service
echo -e "${YELLOW}🔄 Starting the service...${NC}"
systemctl start foxybot.service

# Wait for service to start
echo -e "${YELLOW}🔄 Waiting for service to start...${NC}"
sleep 3

# Check service status
echo -e "${YELLOW}🔄 Checking service status...${NC}"
SERVICE_STATUS=$(systemctl is-active foxybot.service)

if [ "$SERVICE_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ Service is running!${NC}"
    
    # Send notification via Python script
    echo -e "${YELLOW}🔄 Sending notification to admin via Telegram...${NC}"
    
    if [ -f bot/utils/send_notification.py ]; then
        python bot/utils/send_notification.py --message "✅ <b>FoxyVPN Bot</b> has been restarted on server <code>$(hostname)</code> at $(date)."
        echo -e "${GREEN}✅ Restart notification sent to admin${NC}"
    fi
else
    echo -e "${RED}❌ Service failed to start! Status: $SERVICE_STATUS${NC}"
    echo -e "${YELLOW}🔍 Check logs with: journalctl -u foxybot.service -n 50${NC}"
    exit 1
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ FoxyVPN Bot restarted successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}🔍 To view logs:${NC} journalctl -u foxybot.service -f"
echo -e "${BLUE}================================================${NC}" 
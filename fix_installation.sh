#!/bin/bash

# Set colors for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}          FoxyVPN Bot Fix Installation          ${NC}"
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

# Update requirements.txt
echo -e "${YELLOW}🔄 Updating requirements.txt...${NC}"
cat > requirements.txt << EOF
python-telegram-bot==20.7
python-dotenv==1.0.0
requests==2.28.2
sqlalchemy==2.0.15
psycopg2-binary==2.9.5
alembic==1.9.1
python-dateutil==2.8.2
pytz==2023.3
httpx==0.26.0
aiodns==3.1.1
EOF

echo -e "${GREEN}✅ requirements.txt updated successfully${NC}"

# Activate virtual environment
echo -e "${YELLOW}🔄 Activating virtual environment...${NC}"
source venv/bin/activate

# Update libraries
echo -e "${YELLOW}🔄 Updating dependencies...${NC}"
pip install -r requirements.txt

# Create database tables script
echo -e "${YELLOW}🔄 Creating database tables script...${NC}"
mkdir -p db
cat > db/create_tables.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# اضافه کردن مسیر پروژه به سیستم 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import DATABASE_URL
from db.models import Base

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_tables():
    """ایجاد جداول دیتابیس"""
    try:
        # ایجاد موتور دیتابیس
        engine = create_engine(DATABASE_URL)
        
        # ایجاد جداول
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        
        # تست دیتابیس
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        connection = session.connection()
        session.close()
        
        logger.info("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False

if __name__ == "__main__":
    create_tables()
EOF

chmod +x db/create_tables.py
echo -e "${GREEN}✅ Database tables script created${NC}"

# Create database tables
echo -e "${YELLOW}🔄 Creating database tables...${NC}"
python db/create_tables.py

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
        python bot/utils/send_notification.py --message "✅ <b>FoxyVPN Bot</b> installation has been fixed on server <code>$(hostname)</code> at $(date)."
        echo -e "${GREEN}✅ Fix notification sent to admin${NC}"
    fi
else
    echo -e "${RED}❌ Service failed to start! Status: $SERVICE_STATUS${NC}"
    echo -e "${YELLOW}🔍 Check logs with: journalctl -u foxybot.service -n 50${NC}"
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ FoxyVPN Bot installation fixed successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}🔍 To view logs:${NC} journalctl -u foxybot.service -f"
echo -e "${BLUE}================================================${NC}"
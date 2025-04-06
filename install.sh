#!/bin/bash

# Colors used in the script
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Welcome message
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}           FoxyVPN Bot Installer                ${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}This script will automatically install FoxyVPN Bot.${NC}"
echo -e "${YELLOW}Note: You need sudo access to run this script.${NC}"
echo ""

# Check sudo access
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root.${NC}" 
   echo -e "${YELLOW}Please use sudo ./install.sh command.${NC}"
   exit 1
fi

# Set installation directory
INSTALL_DIR="/opt/foxybot"
echo -e "${BLUE}Installation Directory: ${INSTALL_DIR}${NC}"

# Request required information from user
echo ""
echo -e "${BLUE}Please enter the following information:${NC}"
echo ""

# Get bot tokens
read -p "Admin Bot Token: " ADMIN_BOT_TOKEN
read -p "User Bot Token: " USER_BOT_TOKEN

# Get Hiddify panel information
read -p "Hiddify API Version (default: v2): " HIDDIFY_API_VERSION
HIDDIFY_API_VERSION=${HIDDIFY_API_VERSION:-v2}

read -p "Hiddify API Base URL (default: https://panel.hiddify.com): " HIDDIFY_API_BASE_URL
HIDDIFY_API_BASE_URL=${HIDDIFY_API_BASE_URL:-https://panel.hiddify.com}

# Get payment information
read -p "Payment Card Number: " PAYMENT_CARD_NUMBER

# Get database information
read -p "PostgreSQL Username (default: postgres): " DB_USER
DB_USER=${DB_USER:-postgres}

read -p "PostgreSQL Password: " DB_PASSWORD

read -p "Database Name (default: foxybot): " DB_NAME
DB_NAME=${DB_NAME:-foxybot}

read -p "PostgreSQL Server Address (default: localhost): " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "PostgreSQL Port (default: 5432): " DB_PORT
DB_PORT=${DB_PORT:-5432}

# Generate random security keys
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)

# Display summary of entered information
echo ""
echo -e "${BLUE}Information Summary:${NC}"
echo -e "${GREEN}Admin Bot Token:${NC} ${ADMIN_BOT_TOKEN:0:10}..."
echo -e "${GREEN}User Bot Token:${NC} ${USER_BOT_TOKEN:0:10}..."
echo -e "${GREEN}API Version:${NC} ${HIDDIFY_API_VERSION}"
echo -e "${GREEN}API Base URL:${NC} ${HIDDIFY_API_BASE_URL}"
echo -e "${GREEN}Card Number:${NC} ${PAYMENT_CARD_NUMBER}"
echo -e "${GREEN}Database Info:${NC} postgresql://${DB_USER}:******@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo ""

# Confirm information
read -p "Is the above information correct? (y/n): " CONFIRM
if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    echo -e "${RED}Installation canceled.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Installing dependencies...${NC}"

# Install dependencies
apt-get update
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib libpq-dev

echo -e "${GREEN}Dependencies installed successfully.${NC}"
echo ""

# Create database
echo -e "${BLUE}Creating database...${NC}"
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" || true
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" || true

echo -e "${GREEN}Database created successfully.${NC}"
echo ""

# Create installation directory
echo -e "${BLUE}Copying files...${NC}"
mkdir -p ${INSTALL_DIR}
cp -r . ${INSTALL_DIR}

# Create virtual environment and install dependencies
echo -e "${BLUE}Creating virtual environment and installing dependencies...${NC}"
cd ${INSTALL_DIR}
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}Python dependencies installed successfully.${NC}"
echo ""

# Create .env file
echo -e "${BLUE}Creating settings file...${NC}"
cat > ${INSTALL_DIR}/.env << EOL
# Telegram Bot Tokens
ADMIN_BOT_TOKEN=${ADMIN_BOT_TOKEN}
USER_BOT_TOKEN=${USER_BOT_TOKEN}

# PostgreSQL Database Settings
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Security Settings
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Hiddify Panel Settings
HIDDIFY_API_VERSION=${HIDDIFY_API_VERSION}
HIDDIFY_API_BASE_URL=${HIDDIFY_API_BASE_URL}

# Payment Card Number
PAYMENT_CARD_NUMBER=${PAYMENT_CARD_NUMBER}

# Alert Settings
TRAFFIC_ALERT_THRESHOLD=0.85
EXPIRY_ALERT_DAYS=3

# Logging Settings
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE=${INSTALL_DIR}/logs/foxybot.log

# Cron Job Settings
CRON_UPDATE_INTERVAL='*/5 * * * *'
CRON_BACKUP_INTERVAL='0 0 * * *'
EOL

echo -e "${GREEN}Settings file created successfully.${NC}"
echo ""

# Create log directory
mkdir -p ${INSTALL_DIR}/logs

# Create systemd service
echo -e "${BLUE}Creating systemd service...${NC}"
cat > /etc/systemd/system/foxybot.service << EOL
[Unit]
Description=FoxyVPN Telegram Bot
After=network.target postgresql.service

[Service]
User=root
Group=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/bot/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

# Update and enable service
systemctl daemon-reload
systemctl enable foxybot.service
systemctl start foxybot.service

echo -e "${GREEN}Systemd service created and enabled successfully.${NC}"
echo ""

# Display final information
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}FoxyVPN Bot installed successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}Important Information:${NC}"
echo -e "• Installation Path: ${INSTALL_DIR}"
echo -e "• Settings File: ${INSTALL_DIR}/.env"
echo -e "• Logs: ${INSTALL_DIR}/logs/foxybot.log"
echo -e "• Service Status Command: ${GREEN}systemctl status foxybot.service${NC}"
echo -e "• View Logs Command: ${GREEN}journalctl -u foxybot.service -f${NC}"
echo ""
echo -e "${BLUE}Thank you for choosing FoxyVPN!${NC}" 
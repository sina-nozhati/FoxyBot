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

# Check required tools
echo -e "${BLUE}Checking required tools...${NC}"
for tool in curl jq; do
    if ! command -v $tool &> /dev/null; then
        echo -e "${YELLOW}Installing $tool...${NC}"
        apt-get update && apt-get install -y $tool
    fi
done
echo -e "${GREEN}All required tools are installed.${NC}"
echo ""

# Set installation directory
INSTALL_DIR="/opt/foxybot"
echo -e "${BLUE}Installation Directory: ${INSTALL_DIR}${NC}"

# Request required information from user
echo ""
echo -e "${BLUE}Please enter the following information:${NC}"
echo ""

# Function to validate Hiddify panel
validate_hiddify_panel() {
    local domain=$1
    local proxy_path=$2
    local api_key=$3
    
    echo -e "${BLUE}Validating Hiddify panel...${NC}"
    
    # Test using ping endpoint
    local response=$(curl -s -o /dev/null -w "%{http_code}" -H "Hiddify-API-Key: ${api_key}" "https://${domain}/${proxy_path}/api/v2/panel/ping/")
    
    if [[ "$response" == "200" ]]; then
        echo -e "${GREEN}✓ Panel validated successfully!${NC}"
        
        # Get panel info for additional verification
        local panel_info=$(curl -s -H "Hiddify-API-Key: ${api_key}" "https://${domain}/${proxy_path}/api/v2/panel/info/")
        local panel_version=$(echo $panel_info | jq -r '.version // "Unknown"')
        
        echo -e "${GREEN}✓ Panel version: ${panel_version}${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to validate panel. HTTP status: ${response}${NC}"
        echo -e "${YELLOW}Make sure the domain, proxy path and API key are correct.${NC}"
        return 1
    fi
}

# Function to validate Telegram bot token
validate_telegram_token() {
    local token=$1
    local bot_type=$2
    
    echo -e "${BLUE}Validating ${bot_type} Telegram bot...${NC}"
    
    # Get bot info from Telegram API
    local response=$(curl -s "https://api.telegram.org/bot${token}/getMe")
    local success=$(echo $response | jq -r '.ok')
    
    if [[ "$success" == "true" ]]; then
        local bot_username=$(echo $response | jq -r '.result.username')
        local bot_name=$(echo $response | jq -r '.result.first_name')
        
        echo -e "${GREEN}✓ Bot validated successfully!${NC}"
        echo -e "${GREEN}✓ Bot Name: ${bot_name}${NC}"
        echo -e "${GREEN}✓ Username: @${bot_username}${NC}"
        
        # Confirm bot details
        read -p "Is this the correct ${bot_type} bot? (y/n): " confirm
        if [[ $confirm != "y" && $confirm != "Y" ]]; then
            return 1
        fi
        
        return 0
    else
        local error_desc=$(echo $response | jq -r '.description // "Unknown error"')
        echo -e "${RED}✗ Failed to validate bot token: ${error_desc}${NC}"
        return 1
    fi
}

# Get and validate Admin Bot Token
while true; do
    read -p "Admin Bot Token: " ADMIN_BOT_TOKEN
    
    if validate_telegram_token "$ADMIN_BOT_TOKEN" "Admin"; then
        break
    else
        echo -e "${YELLOW}Please enter a valid Admin Bot Token.${NC}"
    fi
done

# Get and validate User Bot Token
while true; do
    read -p "User Bot Token: " USER_BOT_TOKEN
    
    if validate_telegram_token "$USER_BOT_TOKEN" "User"; then
        break
    else
        echo -e "${YELLOW}Please enter a valid User Bot Token.${NC}"
    fi
done

# Validate Hiddify panel information
while true; do
    read -p "Hiddify Panel Domain (without https://): " HIDDIFY_DOMAIN
    read -p "Hiddify Admin Proxy Path: " HIDDIFY_PROXY_PATH
    read -p "Hiddify User Proxy Path: " HIDDIFY_USER_PROXY_PATH
    read -p "Hiddify API Key: " HIDDIFY_API_KEY
    
    if validate_hiddify_panel "$HIDDIFY_DOMAIN" "$HIDDIFY_PROXY_PATH" "$HIDDIFY_API_KEY"; then
        break
    else
        echo -e "${YELLOW}Please enter valid Hiddify panel information.${NC}"
    fi
done

# Construct Hiddify API Base URL
HIDDIFY_API_BASE_URL="https://${HIDDIFY_DOMAIN}"
HIDDIFY_API_VERSION="v2"

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
echo -e "${GREEN}Admin Bot:${NC} Verified ✓"
echo -e "${GREEN}User Bot:${NC} Verified ✓"
echo -e "${GREEN}Hiddify Panel:${NC} Verified ✓"
echo -e "${GREEN}API Version:${NC} ${HIDDIFY_API_VERSION}"
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
HIDDIFY_PROXY_PATH=${HIDDIFY_PROXY_PATH}
HIDDIFY_USER_PROXY_PATH=${HIDDIFY_USER_PROXY_PATH}
HIDDIFY_API_KEY=${HIDDIFY_API_KEY}

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

# Test connections
echo -e "${BLUE}Testing system connections...${NC}"
cd ${INSTALL_DIR}
python3 bot/test_connection.py

if [ $? -ne 0 ]; then
    echo -e "${RED}Connection test failed. Please check your settings and try again.${NC}"
    echo -e "${YELLOW}You can run the test manually with: 'cd ${INSTALL_DIR} && python3 bot/test_connection.py'${NC}"
    
    # Continue anyway?
    read -p "Continue with installation anyway? (y/n): " CONTINUE
    if [[ $CONTINUE != "y" && $CONTINUE != "Y" ]]; then
        echo -e "${RED}Installation canceled.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Connection test passed successfully!${NC}"
fi

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
echo -e "• Test Connection Command: ${GREEN}cd ${INSTALL_DIR} && python3 bot/test_connection.py${NC}"
echo -e "• Service Status Command: ${GREEN}systemctl status foxybot.service${NC}"
echo -e "• View Logs Command: ${GREEN}journalctl -u foxybot.service -f${NC}"
echo ""
echo -e "${BLUE}Thank you for choosing FoxyVPN!${NC}" 
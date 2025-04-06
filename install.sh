#!/bin/bash

# Colors used in the script
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Welcome message
echo -e "${RED}================================================${NC}"
echo -e "${RED}           FoxyVPN Bot Installer                ${NC}"
echo -e "${RED}================================================${NC}"
echo ""

# Installation directory
INSTALL_DIR="/opt/foxybot"

# Check sudo access
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root.${NC}" 
   echo -e "${YELLOW}Please use sudo ./install.sh command.${NC}"
   exit 1
fi

# Check required tools
echo -e "${BLUE}Checking required tools...${NC}"
for tool in curl jq git; do
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
    
    # Call the ping API endpoint
    local response=$(curl -s -o /dev/null -w "%{http_code}" "https://${domain}/${proxy_path}/api/v2/panel/ping/" -H "Hiddify-API-Key: ${api_key}")
    
    if [[ "$response" == "200" ]]; then
        echo -e "${GREEN}✓ Panel validated successfully!${NC}"
        
        # Get panel info for additional verification
        local panel_info=$(curl -s -H "Hiddify-API-Key: ${api_key}" "https://${domain}/${proxy_path}/api/v2/panel/info/")
        local panel_version=$(echo $panel_info | grep -o '"version":"[^"]*' | sed 's/"version":"//g')
        
        echo -e "${GREEN}✓ Panel version: ${panel_version}${NC}"
        
        return 0
    else
        echo -e "${RED}✗ Failed to validate panel. HTTP response: ${response}${NC}"
        return 1
    fi
}

# Function to validate user proxy path with a specific user UUID
validate_user_proxy_path() {
    local domain=$1
    local admin_proxy_path=$2
    local api_key=$3
    local user_proxy_path=$4
    
    echo -e "${BLUE}Validating user proxy path...${NC}"
    
    # First get a user UUID from the panel
    local users_response=$(curl -s "https://${domain}/${admin_proxy_path}/api/v2/admin/user/" -H "Hiddify-API-Key: ${api_key}")
    
    if [[ $users_response == "[]" || $users_response != *"uuid"* ]]; then
        echo -e "${YELLOW}⚠️ No users found in panel. Cannot validate user proxy path.${NC}"
        return 0  # Continue anyway
    fi
    
    # Extract first user UUID
    local user_uuid=$(echo $users_response | grep -o '"uuid":"[^"]*' | head -1 | sed 's/"uuid":"//g')
    local user_name=$(echo $users_response | grep -o '"name":"[^"]*' | head -1 | sed 's/"name":"//g')
    
    if [[ -z "$user_uuid" ]]; then
        echo -e "${YELLOW}⚠️ Could not extract user UUID. Skipping user proxy validation.${NC}"
        return 0  # Continue anyway
    fi
    
    echo -e "${BLUE}Using user: ${user_name} (UUID: ${user_uuid})${NC}"
    
    # Try to access the user profile
    local user_response=$(curl -s "https://${domain}/${user_proxy_path}/${user_uuid}/api/v2/user/me/")
    
    if [[ $user_response == *"profile_title"* ]]; then
        local profile_title=$(echo $user_response | grep -o '"profile_title":"[^"]*' | sed 's/"profile_title":"//g')
        echo -e "${GREEN}✓ User profile validated successfully!${NC}"
        echo -e "${GREEN}✓ Profile title: ${profile_title}${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to validate user proxy path. Could not retrieve user profile.${NC}"
        return 1
    fi
}

# Get Telegram Bot tokens
while true; do
    read -p "Enter Admin Bot Token: " ADMIN_BOT_TOKEN
    
    # Validate Admin Bot Token
    echo -e "${BLUE}Validating Admin Bot Token...${NC}"
    response=$(curl -s "https://api.telegram.org/bot${ADMIN_BOT_TOKEN}/getMe")
    
    if [[ $response == *"\"ok\":true"* ]]; then
        bot_username=$(echo $response | grep -o '"username":"[^"]*' | sed 's/"username":"//g')
        echo -e "${GREEN}✓ Admin Bot Token is valid (Bot: @${bot_username})${NC}"
        break
    else
        echo -e "${RED}✗ Invalid Admin Bot Token. Please try again.${NC}"
    fi
done

while true; do
    read -p "Enter User Bot Token: " USER_BOT_TOKEN
    
    # Validate User Bot Token
    echo -e "${BLUE}Validating User Bot Token...${NC}"
    response=$(curl -s "https://api.telegram.org/bot${USER_BOT_TOKEN}/getMe")
    
    if [[ $response == *"\"ok\":true"* ]]; then
        bot_username=$(echo $response | grep -o '"username":"[^"]*' | sed 's/"username":"//g')
        echo -e "${GREEN}✓ User Bot Token is valid (Bot: @${bot_username})${NC}"
        break
    else
        echo -e "${RED}✗ Invalid User Bot Token. Please try again.${NC}"
    fi
done

while true; do
    # دریافت لینک کامل پنل و استخراج اجزای آن
    read -p "Enter complete Hiddify Admin Panel URL (e.g., https://domain.com/admin_path/api_key/): " HIDDIFY_FULL_URL

    # استخراج اجزای URL
    if [[ $HIDDIFY_FULL_URL =~ https?://([^/]+)/([^/]+)/([^/]+) ]]; then
        HIDDIFY_DOMAIN="${BASH_REMATCH[1]}"
        HIDDIFY_PROXY_PATH="${BASH_REMATCH[2]}"
        HIDDIFY_API_KEY="${BASH_REMATCH[3]}"
        
        echo -e "${GREEN}✅ Successfully extracted panel information:${NC}"
        echo -e "Domain: ${HIDDIFY_DOMAIN}"
        echo -e "Admin Proxy Path: ${HIDDIFY_PROXY_PATH}"
        echo -e "API Key: ${HIDDIFY_API_KEY}"
        
        # اعتبارسنجی پنل
        if validate_hiddify_panel "$HIDDIFY_DOMAIN" "$HIDDIFY_PROXY_PATH" "$HIDDIFY_API_KEY"; then
            break
        fi
    else
        echo -e "${RED}❌ Failed to parse URL. Please enter valid URL format.${NC}"
    fi
done

# Construct Hiddify API Base URL
HIDDIFY_API_BASE_URL="https://${HIDDIFY_DOMAIN}"
HIDDIFY_API_VERSION="v2"

# دریافت مسیر پروکسی کاربران
while true; do
    read -p "Enter User Proxy Path: " HIDDIFY_USER_PROXY_PATH
    
    # اعتبارسنجی مسیر پروکسی کاربران
    if validate_user_proxy_path "$HIDDIFY_DOMAIN" "$HIDDIFY_PROXY_PATH" "$HIDDIFY_API_KEY" "$HIDDIFY_USER_PROXY_PATH"; then
        break
    else
        echo -e "${YELLOW}Would you like to try again or continue anyway? (t/c): ${NC}"
        read -p "" TC_ANSWER
        if [[ "$TC_ANSWER" == "c" ]]; then
            break
        fi
    fi
done

# Get payment information
read -p "Payment Card Number: " PAYMENT_CARD_NUMBER

# Get admin telegram ID for notifications
read -p "Admin Telegram ID (for notifications): " ADMIN_TELEGRAM_ID

# Get database information
read -p "PostgreSQL Username (default: postgres): " DB_USER
DB_USER=${DB_USER:-postgres}

read -p "PostgreSQL Password (default: admin1234): " DB_PASSWORD
DB_PASSWORD=${DB_PASSWORD:-admin1234}

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

# Initialize database
echo -e "${YELLOW}Creating database tables...${NC}"
python3 db/create_tables.py

# Create installation directory
echo -e "${BLUE}Setting up installation directory...${NC}"
mkdir -p ${INSTALL_DIR}

# Check if we are running from the cloned repo or standalone script
if [ -d "./bot" ] && [ -f "./requirements.txt" ]; then
    echo -e "${BLUE}Copying files from current directory...${NC}"
    cp -r . ${INSTALL_DIR}
else
    echo -e "${BLUE}Downloading the latest version from GitHub...${NC}"
    # Install git if needed
    if ! command -v git &> /dev/null; then
        echo -e "${YELLOW}Installing git...${NC}"
        apt-get update && apt-get install -y git
    fi
    
    # Clone the repository
    git clone https://github.com/sina-nozhati/FoxyBot.git ${INSTALL_DIR}/temp
    
    # Move files from the cloned directory to the installation directory
    cp -r ${INSTALL_DIR}/temp/* ${INSTALL_DIR}/
    cp -r ${INSTALL_DIR}/temp/.gitignore ${INSTALL_DIR}/ 2>/dev/null || :
    
    # Remove temporary directory
    rm -rf ${INSTALL_DIR}/temp
fi

echo -e "${GREEN}Files copied to ${INSTALL_DIR} successfully.${NC}"

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
if [ -f "${INSTALL_DIR}/bot/test_connection.py" ]; then
    cd ${INSTALL_DIR}
    # Make sure dependencies are installed
    source venv/bin/activate
    
    # Install required packages for test if needed
    pip install requests python-dotenv psycopg2-binary
    
    # Run the test
    python3 bot/test_connection.py
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -ne 0 ]; then
        echo -e "${RED}Connection test failed. Please check your settings and try again.${NC}"
        echo -e "${YELLOW}You can run the test manually with: 'cd ${INSTALL_DIR} && source venv/bin/activate && python3 bot/test_connection.py'${NC}"
        
        # Continue anyway?
        read -p "Continue with installation anyway? (y/n): " CONTINUE
        if [[ $CONTINUE != "y" && $CONTINUE != "Y" ]]; then
            echo -e "${RED}Installation canceled.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Connection test passed successfully!${NC}"
    fi
else
    echo -e "${RED}Cannot find test_connection.py script. Skipping connection test.${NC}"
    echo -e "${YELLOW}After installation, you can run the test manually with: 'cd ${INSTALL_DIR} && source venv/bin/activate && python3 bot/test_connection.py'${NC}"
    
    # Continue anyway?
    read -p "Continue with installation anyway? (y/n): " CONTINUE
    if [[ $CONTINUE != "y" && $CONTINUE != "Y" ]]; then
        echo -e "${RED}Installation canceled.${NC}"
        exit 1
    fi
fi

# Create systemd service
echo -e "${BLUE}Creating systemd service...${NC}"
cat > /etc/systemd/system/foxybot.service << EOL
[Unit]
Description=FoxyVPN Telegram Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
User=root
Group=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/bot/main.py
Environment=PYTHONPATH=${INSTALL_DIR}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
TimeoutStartSec=60
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOL

# Update and enable service
systemctl daemon-reload
systemctl enable foxybot.service
systemctl start foxybot.service

# Check if the service is running
echo -e "${BLUE}Checking service status...${NC}"
sleep 5  # Give the service some time to start
service_status=$(systemctl is-active foxybot.service)

if [ "$service_status" == "active" ]; then
    echo -e "${GREEN}Service is running successfully!${NC}"
else
    echo -e "${RED}Service is not running! Status: ${service_status}${NC}"
    echo -e "${YELLOW}Please check logs with: journalctl -u foxybot.service -n 50${NC}"
    
    # Continue anyway?
    read -p "Continue anyway? (y/n): " CONTINUE
    if [[ $CONTINUE != "y" && $CONTINUE != "Y" ]]; then
        echo -e "${RED}Installation completed but service is not running properly.${NC}"
    fi
fi

# Send notification to admin
echo -e "${BLUE}Sending notification to Admin via Telegram...${NC}"
curl -s -X POST "https://api.telegram.org/bot${ADMIN_BOT_TOKEN}/sendMessage" \
    -d chat_id="${ADMIN_TELEGRAM_ID:-0}" \
    -d text="🎉 FoxyVPN Bot has been successfully installed!
    
🖥️ Server Info:
• Hostname: $(hostname)
• IP: $(curl -s ifconfig.me)

⚙️ Installation Details:
• Path: ${INSTALL_DIR}
• Hiddify Panel: ${HIDDIFY_API_BASE_URL}
• Database: ${DB_NAME}

Use /start command to begin using the bot.
" \
    -d parse_mode="Markdown" > /dev/null

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
echo -e "• Test Connection Command: ${GREEN}cd ${INSTALL_DIR} && source venv/bin/activate && python3 bot/test_connection.py${NC}"
echo -e "• Service Status Command: ${GREEN}systemctl status foxybot.service${NC}"
echo -e "• View Logs Command: ${GREEN}journalctl -u foxybot.service -f${NC}"
echo ""
echo -e "${BLUE}Thank you for choosing FoxyVPN!${NC}" 
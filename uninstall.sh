#!/bin/bash

# Colors used in the script
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Welcome message
echo -e "${RED}================================================${NC}"
echo -e "${RED}           FoxyVPN Bot Uninstaller              ${NC}"
echo -e "${RED}================================================${NC}"
echo -e "${YELLOW}WARNING: This script will completely remove FoxyVPN Bot from your system!${NC}"
echo -e "${YELLOW}It will:${NC}"
echo -e "${YELLOW}  - Stop and remove the systemd service${NC}"
echo -e "${YELLOW}  - Delete all program files${NC}"
echo -e "${YELLOW}  - Drop the PostgreSQL database${NC}"
echo -e "${YELLOW}  - Remove all logs${NC}"
echo ""

# Check sudo access
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root.${NC}" 
   echo -e "${YELLOW}Please use sudo ./uninstall.sh command.${NC}"
   exit 1
fi

# Installation directory
INSTALL_DIR="/opt/foxybot"

# Confirm uninstallation
echo -e "${RED}This action cannot be undone!${NC}"
read -p "Are you sure you want to uninstall FoxyVPN Bot? (y/n): " CONFIRM
if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    echo -e "${GREEN}Uninstallation canceled.${NC}"
    exit 0
fi

# Get database information
read -p "PostgreSQL Username (default: postgres): " DB_USER
DB_USER=${DB_USER:-postgres}

read -p "PostgreSQL Password: " DB_PASSWORD

read -p "Database Name (default: foxybot): " DB_NAME
DB_NAME=${DB_NAME:-foxybot}

# Step 1: Stop and disable the service
echo -e "${BLUE}Stopping and disabling FoxyVPN Bot service...${NC}"
systemctl stop foxybot.service
systemctl disable foxybot.service
rm -f /etc/systemd/system/foxybot.service
systemctl daemon-reload
echo -e "${GREEN}Service stopped and removed.${NC}"

# Step 2: Drop the database
echo -e "${BLUE}Dropping PostgreSQL database...${NC}"
if PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;" postgres; then
    echo -e "${GREEN}Database dropped successfully.${NC}"
else
    echo -e "${RED}Failed to drop database.${NC}"
    echo -e "${YELLOW}You may need to manually drop it using: DROP DATABASE $DB_NAME;${NC}"
fi

# Step 3: Send notification to admin about uninstall (if config exists)
if [ -f "$INSTALL_DIR/.env" ]; then
    echo -e "${BLUE}Sending uninstallation notification to admin...${NC}"
    
    # Source the environment variables
    source $INSTALL_DIR/.env
    
    # Check if we have the admin token and ID
    if [ ! -z "$ADMIN_BOT_TOKEN" ] && [ ! -z "$ADMIN_TELEGRAM_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${ADMIN_BOT_TOKEN}/sendMessage" \
            -d chat_id="${ADMIN_TELEGRAM_ID}" \
            -d text="⚠️ FoxyVPN Bot has been uninstalled from server $(hostname)." > /dev/null
    fi
fi

# Step 4: Remove installation directory
echo -e "${BLUE}Removing installation directory...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}Installation directory removed.${NC}"
else
    echo -e "${YELLOW}Installation directory not found.${NC}"
fi

# Step 5: Clean up logs
echo -e "${BLUE}Cleaning up logs...${NC}"
journalctl --vacuum-time=1s --unit=foxybot.service
echo -e "${GREEN}Logs cleaned.${NC}"

# Summary
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}FoxyVPN Bot has been completely uninstalled!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}The following items have been removed:${NC}"
echo -e "• Systemd service: foxybot.service"
echo -e "• Installation directory: ${INSTALL_DIR}"
echo -e "• PostgreSQL database: ${DB_NAME}"
echo -e "• All related logs"
echo ""
echo -e "${BLUE}Thank you for using FoxyVPN!${NC}" 
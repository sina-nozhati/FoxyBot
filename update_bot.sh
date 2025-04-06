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

# Update code from Git
echo -e "${YELLOW}🔄 Updating code from GitHub...${NC}"
git pull

# Activate virtual environment
echo -e "${YELLOW}🔄 Activating virtual environment...${NC}"
source venv/bin/activate

# Update libraries
echo -e "${YELLOW}🔄 Updating dependencies...${NC}"
pip install -r requirements.txt

# Restart the service
echo -e "${YELLOW}🔄 Restarting the service...${NC}"
systemctl start foxybot.service

# Check service status
echo -e "${YELLOW}🔄 Checking service status...${NC}"
systemctl status foxybot.service --no-pager

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ FoxyVPN Bot updated successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}🔍 To view logs:${NC} journalctl -u foxybot.service -f"
echo -e "${BLUE}================================================${NC}"
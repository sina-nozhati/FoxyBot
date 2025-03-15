#!/bin/bash
# FoxyBot Installation Script
# This script allows users to choose between the legacy and current versions

# Define text colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RESET='\033[0m' # Reset text color

REPO_URL="https://github.com/sina-nozhati/FoxyBot.git"
INSTALL_DIR="/opt/Hiddify-Telegram-Bot"

# Function to display error messages and exit
function display_error_and_exit() {
  echo -e "${RED}Error: $1${RESET}"
  exit 1
}

# Function to install Git if needed
install_git_if_needed() {
  if ! command -v git &>/dev/null; then
    echo "Git is not installed. Installing Git..."

    # Install Git based on the operating system (Linux)
    if [ -f /etc/os-release ]; then
      source /etc/os-release
      if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
        sudo apt update
        sudo apt install -y git
      elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
        sudo yum install -y git
      fi
    elif [ "$(uname -s)" == "Darwin" ]; then # macOS
      brew install git
    else
      echo "Unsupported operating system. Please install Git manually and try again."
      exit 1
    fi

    if ! command -v git &>/dev/null; then
      echo "Failed to install Git. Please install Git manually and try again."
      exit 1
    fi

    echo "Git has been installed successfully."
  fi
}

# Check parameters
version="current"
branch="main"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --legacy)
      version="legacy"
      shift
      ;;
    --current)
      version="current"
      shift
      ;;
    --pre-release)
      branch="pre-release"
      shift
      ;;
    *)
      # Unknown option
      echo -e "${RED}Unknown option: $1${RESET}"
      echo "Usage: $0 [--legacy|--current] [--pre-release]"
      exit 1
      ;;
  esac
done

# Display banner
echo -e "${BLUE}=======================================${RESET}"
echo -e "${BLUE}    FoxyBot Installation Script       ${RESET}"
echo -e "${BLUE}=======================================${RESET}"
echo

# Install prerequisites
echo -e "${GREEN}Step 0: Checking requirements...${RESET}"
install_git_if_needed

# Check if Python 3 and pip are installed
if ! command -v python3 &>/dev/null || ! command -v pip &>/dev/null; then
  echo "Python 3 and pip are required. Installing Python 3 and pip..."

  # Install Python 3 and pip based on the operating system (Linux)
  if [ -f /etc/os-release ]; then
    source /etc/os-release
    if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
      sudo apt update
      sudo apt install -y python3 python3-pip python3-venv
    elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
      sudo yum install -y python3 python3-pip
    fi
  elif [ "$(uname -s)" == "Darwin" ]; then # macOS
    brew install python@3
  else
    echo "Unsupported operating system. Please install Python 3 and pip manually and try again."
    exit 1
  fi
fi

# Check if Git is installed
if ! command -v git &>/dev/null; then
  display_error_and_exit "Git is not installed. Please install Git and try again."
fi

# Check if Python 3 and pip are installed
if ! command -v python3 &>/dev/null || ! command -v pip &>/dev/null; then
  display_error_and_exit "Python 3 and pip are required. Please install them and try again."
fi

# Show selected version
if [ "$version" == "legacy" ]; then
  echo -e "${YELLOW}Selected version: Legacy (Old Version)${RESET}"
  install_script_path="legacy/install.sh"
else
  echo -e "${YELLOW}Selected version: Current (New Version)${RESET}"
  install_script_path="current/install.sh"
fi

echo -e "${YELLOW}Selected branch: $branch${RESET}"

# Create a temporary directory
temp_dir=$(mktemp -d)
echo "Created temporary directory: $temp_dir"

# Clone the repository
echo -e "${GREEN}Step 1: Cloning the repository...${RESET}"
git clone -b $branch $REPO_URL $temp_dir || display_error_and_exit "Failed to clone the repository"

# Check if the script for the selected version exists
if [ ! -f "$temp_dir/$install_script_path" ]; then
  display_error_and_exit "Installation script for the selected version not found!"
fi

# Make the install script executable
chmod +x "$temp_dir/$install_script_path"

# Ask if user wants to keep existing configuration
if [ -d "$INSTALL_DIR" ]; then
  echo -e "${YELLOW}An existing installation was detected at $INSTALL_DIR${RESET}"
  echo -e "${YELLOW}Do you want to backup existing configuration? (y/n)${RESET}"
  read backup_config
  
  if [ "$backup_config" == "y" ] || [ "$backup_config" == "Y" ]; then
    backup_dir="$HOME/foxybot_backup_$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}Backing up to $backup_dir...${RESET}"
    mkdir -p "$backup_dir"
    if [ -d "$INSTALL_DIR/Database" ]; then
      cp -r "$INSTALL_DIR/Database" "$backup_dir/"
    fi
    if [ -f "$INSTALL_DIR/config.json" ]; then
      cp "$INSTALL_DIR/config.json" "$backup_dir/"
    fi
    echo -e "${GREEN}Backup completed${RESET}"
  fi
fi

# Execute the installation script for the selected version
echo -e "${GREEN}Step 2: Running installation script for $version version...${RESET}"
cd "$temp_dir/$(dirname $install_script_path)" || display_error_and_exit "Failed to change directory"

# Execute the specific install script
chmod +x $(basename $install_script_path)
./$(basename $install_script_path) || display_error_and_exit "Installation failed"

# Clean up the temporary directory
echo -e "${GREEN}Cleaning up temporary files...${RESET}"
rm -rf "$temp_dir"

echo -e "${GREEN}Installation completed successfully!${RESET}"
echo -e "${GREEN}You can start using FoxyBot by sending /start to your Telegram bot.${RESET}"
echo -e "${BLUE}=======================================${RESET}"
echo -e "${BLUE}    Installation Complete!            ${RESET}"
echo -e "${BLUE}=======================================${RESET}" 
#!/bin/bash

# Define text colors
GREEN='\033[0;32m'
RED='\033[0;31m'
RESET='\033[0m' # Reset text color
install_dir="/opt/Hiddify-Telegram-Bot"

# Function to display error messages and exit
function display_error_and_exit() {
  echo -e "${RED}Error: $1${RESET}"
  exit 1
}

# Check if Python 3 is installed
if ! command -v python3 &>/dev/null; then
  display_error_and_exit "Python 3 is required. Please install it and try again."
fi

# Check if virtual environment exists
if [ -d "$install_dir/venv" ]; then
  use_venv=true
  echo -e "${GREEN}Virtual environment detected. Using it for bot restart.${RESET}"
else
  use_venv=false
  echo -e "${GREEN}No virtual environment detected. Using system Python.${RESET}"
fi

# Stop the bot gracefully using SIGTERM (signal 15)
echo -e "${GREEN}Stopping the bot gracefully...${RESET}"
pkill -15 -f hiddifyTelegramBot.py

# Wait for a few seconds to allow the bot to terminate
echo "Please wait for 5 seconds ..."
sleep 5

# Start the bot and redirect output to a log file
echo -e "${GREEN}Starting the bot...${RESET}"

> $install_dir/bot.log

# Use virtual environment if it exists, otherwise use system Python
if [ "$use_venv" = true ]; then
  echo "Starting bot with virtual environment..."
  nohup bash -c "source $install_dir/venv/bin/activate && python3 $install_dir/hiddifyTelegramBot.py >> $install_dir/bot.log 2>&1" &
else
  nohup python3 /opt/Hiddify-Telegram-Bot/hiddifyTelegramBot.py >> /opt/Hiddify-Telegram-Bot/bot.log 2>&1 &
fi

echo -e "${GREEN}Bot has been restarted.${RESET}"

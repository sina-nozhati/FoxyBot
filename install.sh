 #!/bin/bash
# Define text colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m' # Reset text color

HIDY_BOT_ID="@HidyBotGroup"
# Function to display error messages and exit
function display_error_and_exit() {
  echo -e "${RED}Error: $1${RESET}"
  echo -e "${YELLOW}${HIDY_BOT_ID}${RESET}"
  exit 1
}

install_git_if_needed() {
  if ! command -v git &>/dev/null; then
    echo "Git is not installed. Installing Git..."

    # Install Git based on the operating system (Linux)
    if [ -f /etc/os-release ]; then
      source /etc/os-release
      if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
        apt update
        apt install -y git
      elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
        yum install -y git
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

# Function to install Python 3 and pip if they are not already installed
install_python3_and_pip_if_needed() {
  if ! command -v python3 &>/dev/null || ! command -v pip &>/dev/null; then
    echo "Python 3 and pip are required. Installing Python 3 and pip..."

    # Install Python 3 and pip based on the operating system (Linux)
    if [ -f /etc/os-release ]; then
      source /etc/os-release
      if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
        apt update
        apt install -y python3 python3-pip python3-setuptools python3-dev
        
        # Determine Python version and install corresponding venv package
        python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
        apt install -y python3-venv
        apt install -y python${python_version}-venv || echo "Warning: Could not install python${python_version}-venv, continuing..."
      elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
        yum install -y python3 python3-pip python3-devel
      fi
    elif [ "$(uname -s)" == "Darwin" ]; then # macOS
      brew install python@3
    else
      echo "Unsupported operating system. Please install Python 3 and pip manually and try again."
      exit 1
    fi

    if ! command -v python3 &>/dev/null || ! command -v pip &>/dev/null; then
      echo "Failed to install Python 3 and pip. Please install Python 3 and pip manually and try again."
      exit 1
    fi

    echo "Python 3 and pip have been installed successfully."
  fi
}

echo -e "${GREEN}Step 0: Checking requirements...${RESET}"
install_git_if_needed
install_python3_and_pip_if_needed

# Check if Git is installed
if ! command -v git &>/dev/null; then
  display_error_and_exit "Git is not installed. Please install Git and try again."
fi

# Check if Python 3 and pip are installed
if ! command -v python3 &>/dev/null || ! command -v pip &>/dev/null; then
  display_error_and_exit "Python 3 and pip are required. Please install them and try again."
fi

echo -e "${GREEN}Step 1: Cloning the repository and changing directory...${RESET}"

repository_url="https://github.com/sina-nozhati/FoxyBot.git"
install_dir="/opt/Hiddify-Telegram-Bot"
bot_dir="Foxybot/current" # Path to the bot directory inside the repository

branch="main"

if [ "$1" == "--pre-release" ]; then
    branch="pre-release"
fi

echo "Selected branch: $branch"

# Remove existing directory if it exists
if [ -d "$install_dir" ]; then
  echo "Removing existing directory $install_dir"
  rm -rf "$install_dir"
fi

# Create temporary directory for cloning
temp_dir=$(mktemp -d)
echo "Cloning repository..."
git clone -b "$branch" "$repository_url" "$temp_dir" || display_error_and_exit "Failed to clone the repository."

# Check if the bot directory exists in the repository
if [ ! -d "$temp_dir/$bot_dir" ]; then
  display_error_and_exit "Bot directory '$bot_dir' not found in repository"
fi

# Create install directory
mkdir -p "$install_dir"

# Copy files from the bot directory to the install directory
echo "Copying files from $temp_dir/$bot_dir to $install_dir"
cp -r "$temp_dir/$bot_dir"/* "$install_dir/" || display_error_and_exit "Failed to copy files"

# Clean up temporary directory
rm -rf "$temp_dir"

# Change to the installation directory
cd "$install_dir" || display_error_and_exit "Failed to change directory."

# Verify the files
echo "Verifying files..."
if [ ! -f "hiddifyTelegramBot.py" ]; then
    display_error_and_exit "hiddifyTelegramBot.py not found in repository"
fi

# Check if config.json exists or create a minimal one
if [ ! -f "config.json" ]; then
    echo "Creating minimal config.json file"
    cat > config.json << 'EOL'
{
  "admin_id": 0,
  "token": "",
  "database": "Database/database.db",
  "log_file": "Logs/bot.log",
  "user_log_file": "Logs/user_bot.log",
  "admin_log_file": "Logs/admin_bot.log",
  "backup_dir": "Database/Backup",
  "max_file_size": 50,
  "allowed_hosts": ["x8.hiddify.com"],
  "is_debug_mode": true
}
EOL
fi

echo "Files verified successfully"

echo -e "${GREEN}Step 2: Creating and activating virtual environment...${RESET}"
python3 -m venv venv || display_error_and_exit "Failed to create virtual environment."
source venv/bin/activate || display_error_and_exit "Failed to activate virtual environment."

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel || echo "Warning: Failed to upgrade pip, setuptools, and wheel"

echo -e "${GREEN}Step 3: Installing requirements...${RESET}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt || echo "Warning: Failed to install some requirements. Trying alternative method..."
    
    # Try to install requirements individually
    pip install psutil || echo "Warning: Failed to install psutil"
    pip install pyTelegramBotAPI --no-build-isolation || echo "Warning: Failed to install pyTelegramBotAPI"
    pip install requests || echo "Warning: Failed to install requests"
    pip install termcolor || echo "Warning: Failed to install termcolor"
    pip install qrcode || echo "Warning: Failed to install qrcode"
    pip install pytz || echo "Warning: Failed to install pytz"
else
    echo "requirements.txt not found, installing common requirements..."
    pip install psutil pyTelegramBotAPI requests termcolor qrcode pytz
fi

echo -e "${GREEN}Step 4: Preparing directories...${RESET}"
logs_dir="$install_dir/Logs"
receiptions_dir="$install_dir/UserBot/Receiptions"

create_directory_if_not_exists() {
  if [ ! -d "$1" ]; then
    echo "Creating directory $1"
    mkdir -p "$1"
  fi
}

create_directory_if_not_exists "$logs_dir"
create_directory_if_not_exists "$receiptions_dir"
create_directory_if_not_exists "$install_dir/Database"
create_directory_if_not_exists "$install_dir/Database/Backup"

# Make sure restart.sh and update.sh are executable if they exist
if [ -f "$install_dir/restart.sh" ]; then
    chmod +x "$install_dir/restart.sh"
fi

if [ -f "$install_dir/update.sh" ]; then
    chmod +x "$install_dir/update.sh"
fi

echo -e "${GREEN}Step 5: Setting up configuration...${RESET}"
# Prompt for bot token and admin ID if config is empty
if grep -q '"token": ""' config.json; then
    echo "Please enter your Telegram bot token:"
    read -r token
    sed -i "s/\"token\": \"\"/\"token\": \"$token\"/g" config.json
fi

if grep -q '"admin_id": 0' config.json; then
    echo "Please enter your Telegram admin ID:"
    read -r admin_id
    sed -i "s/\"admin_id\": 0/\"admin_id\": $admin_id/g" config.json
fi

echo -e "${GREEN}Step 6: Running the bot in the background...${RESET}"
# Create a new log file for the current run
echo "Starting bot at $(date)" > "$install_dir/bot.log"
echo "Python version: $(python3 --version)" >> "$install_dir/bot.log"
echo "Virtual environment: $VIRTUAL_ENV" >> "$install_dir/bot.log"
echo "Current directory: $(pwd)" >> "$install_dir/bot.log"

# Run the bot with more detailed logging
nohup bash -c "source venv/bin/activate && python3 hiddifyTelegramBot.py >> $install_dir/bot.log 2>&1" &

echo -e "${GREEN}Step 7: Adding cron jobs...${RESET}"

add_cron_job_if_not_exists() {
  local cron_job="$1"
  local current_crontab

  # Normalize the cron job formatting (remove extra spaces)
  cron_job=$(echo "$cron_job" | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')

  # Check if the cron job already exists in the current user's crontab
  current_crontab=$(crontab -l 2>/dev/null || true)

  if [[ -z "$current_crontab" ]]; then
    # No existing crontab, so add the new cron job
    (echo "$cron_job") | crontab -
  elif ! (echo "$current_crontab" | grep -Fq "$cron_job"); then
    # Cron job doesn't exist, so append it to the crontab
    (echo "$current_crontab"; echo "$cron_job") | crontab -
  fi
}

# Add cron job for reboot
add_cron_job_if_not_exists "@reboot cd $install_dir && source venv/bin/activate && bash ./restart.sh"

# Add cron job to run every 6 hours
add_cron_job_if_not_exists "0 */6 * * * cd $install_dir && source venv/bin/activate && python3 crontab.py --backup"

# Add cron job to run at 12:00 PM daily
add_cron_job_if_not_exists "0 12 * * * cd $install_dir && source venv/bin/activate && python3 crontab.py --reminder"

echo -e "${GREEN}Waiting for a few seconds...${RESET}"
sleep 10

# Check if the bot process is running
if pgrep -f "python3 hiddifyTelegramBot.py" >/dev/null; then
  echo -e "${GREEN}The bot has been started successfully.${RESET}"
  echo -e "${GREEN}Send [/start] in Telegram bot.${RESET}"
  echo -e "${GREEN}You can check the logs at: $install_dir/bot.log${RESET}"
else
  echo -e "${RED}Failed to start the bot. Checking logs...${RESET}"
  if [ -f "$install_dir/bot.log" ]; then
    echo -e "${YELLOW}Last 10 lines of bot.log:${RESET}"
    tail -n 10 "$install_dir/bot.log"
  fi
  display_error_and_exit "Failed to start the bot. Please check for errors and try again."
fi
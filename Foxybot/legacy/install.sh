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
  if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
    echo "Python 3 and pip are required. Installing Python 3 and pip..."

    # Install Python 3 and pip based on the operating system (Linux)
    if [ -f /etc/os-release ]; then
      source /etc/os-release
      if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
        apt update
        apt install -y python3 python3-pip python3-venv python3-dev
      elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
        yum install -y python3 python3-pip python3-devel
      fi
    elif [ "$(uname -s)" == "Darwin" ]; then # macOS
      brew install python@3
    else
      echo "Unsupported operating system. Please install Python 3 and pip manually and try again."
      exit 1
    fi

    if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
      echo "Failed to install Python 3 and pip. Please install Python 3 and pip manually and try again."
      exit 1
    fi

    echo "Python 3 and pip have been installed successfully."
  fi
}

# Function to create and set up a virtual environment
setup_virtual_environment() {
  echo "Setting up a Python virtual environment..."
  
  # Install python3-venv if needed
  if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "Installing python3-venv..."
    if [ -f /etc/os-release ]; then
      source /etc/os-release
      if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
        apt install -y python3-venv
      elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
        yum install -y python3-venv
      fi
    fi
  fi
  
  # Create virtual environment
  python3 -m venv "$install_dir/venv" || display_error_and_exit "Failed to create virtual environment."
  
  # Activate virtual environment
  source "$install_dir/venv/bin/activate" || display_error_and_exit "Failed to activate virtual environment."
  
  # Upgrade essential packages
  python -m pip install --upgrade pip setuptools wheel || echo "Warning: Failed to upgrade pip, setuptools, and wheel, but continuing installation."
  
  echo "Virtual environment has been set up successfully."
}

# Alternative method to install packages
install_packages_alternative() {
  echo "Trying alternative installation method..."
  
  # Try installing with system package manager first
  if [ -f /etc/os-release ]; then
    source /etc/os-release
    if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
      apt update
      apt install -y python3-psutil python3-requests python3-qrcode python3-pytz python3-termcolor
      pip install pyTelegramBotAPI==4.12.0 --no-deps
      return 0
    fi
  fi
  
  # If system package manager doesn't work, try installing individually
  pip install psutil==5.9.4 || echo "Warning: Failed to install psutil"
  pip install requests==2.30.0 || echo "Warning: Failed to install requests"
  pip install termcolor==2.3.0 || echo "Warning: Failed to install termcolor"
  pip install qrcode==7.4.2 || echo "Warning: Failed to install qrcode"
  pip install pytz==2023.3.post1 || echo "Warning: Failed to install pytz"
  pip install pyTelegramBotAPI==4.12.0 --no-build-isolation || pip install pyTelegramBotAPI==4.14.0 || echo "Warning: Failed to install pyTelegramBotAPI"
  
  return 0
}

echo -e "${GREEN}Step 0: Checking requirements...${RESET}"
install_git_if_needed
install_python3_and_pip_if_needed

# Check if Git is installed
if ! command -v git &>/dev/null; then
  display_error_and_exit "Git is not installed. Please install Git and try again."
fi

# Check if Python 3 and pip are installed
if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null; then
  display_error_and_exit "Python 3 and pip are required. Please install them and try again."
fi

echo -e "${GREEN}Step 1: Cloning the repository and changing directory...${RESET}"

repository_url="https://github.com/B3H1Z/Hiddify-Telegram-Bot.git"
install_dir="/opt/Hiddify-Telegram-Bot"

branch="main"

if [ "$1" == "--pre-release" ]; then
    branch="pre-release"
fi

echo "Selected branch: $branch"

if [ -d "$install_dir" ]; then
  echo "Directory $install_dir exists."
else
  git clone -b "$branch" "$repository_url" "$install_dir" || display_error_and_exit "Failed to clone the repository."
fi

cd "$install_dir" || display_error_and_exit "Failed to change directory."

echo -e "${GREEN}Step 2: Setting up virtual environment...${RESET}"
setup_virtual_environment

echo -e "${GREEN}Step 3: Installing requirements...${RESET}"
pip install -r requirements.txt || install_packages_alternative

echo -e "${GREEN}Step 4: Preparing ...${RESET}"
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

chmod +x "$install_dir/restart.sh"
chmod +x "$install_dir/update.sh"

# Create a wrapper script to run commands with the virtual environment
cat > "$install_dir/run_with_venv.sh" << 'EOL'
#!/bin/bash
source "$(dirname "$0")/venv/bin/activate"
exec "$@"
EOL
chmod +x "$install_dir/run_with_venv.sh"

# Update the restart script to use the virtual environment
sed -i 's|python3 hiddifyTelegramBot.py|./run_with_venv.sh python3 hiddifyTelegramBot.py|g' "$install_dir/restart.sh" || echo "Warning: Failed to update restart script."

echo -e "${GREEN}Step 5: Running config.py to generate config.json...${RESET}"
source "$install_dir/venv/bin/activate" 
python3 config.py || display_error_and_exit "Failed to run config.py."

echo -e "${GREEN}Step 6: Running the bot in the background...${RESET}"
nohup ./run_with_venv.sh python3 hiddifyTelegramBot.py >>$install_dir/bot.log 2>&1 &

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
add_cron_job_if_not_exists "@reboot cd $install_dir && ./restart.sh"

# Add cron job to run every 6 hours - with virtual environment
add_cron_job_if_not_exists "0 */6 * * * cd $install_dir && ./run_with_venv.sh python3 crontab.py --backup"

# Add cron job to run at 12:00 PM daily - with virtual environment
add_cron_job_if_not_exists "0 12 * * * cd $install_dir && ./run_with_venv.sh python3 crontab.py --reminder"

echo -e "${GREEN}Waiting for a few seconds...${RESET}"
sleep 5

if pgrep -f "python3 hiddifyTelegramBot.py" >/dev/null; then
  echo -e "${GREEN}The bot has been started successfully.${RESET}"
  echo -e "${GREEN}Send [/start] in Telegram bot.${RESET}"
else
  display_error_and_exit "Failed to start the bot. Please check for errors and try again."
fi

# Deactivate virtual environment
deactivate
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

# Function to install Python 3 and pip if they are not already installed
install_python3_and_pip_if_needed() {
  if ! command -v python3 &>/dev/null || ! command -v pip &>/dev/null; then
    echo "Python 3 and pip are required. Installing Python 3 and pip..."

    # Install Python 3 and pip based on the operating system (Linux)
    if [ -f /etc/os-release ]; then
      source /etc/os-release
      if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
        sudo apt update
        sudo apt install -y python3 python3-pip python3-dev build-essential python3-setuptools python3-wheel python3-venv python3-full
      elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
        sudo yum install -y python3 python3-pip python3-devel gcc python3-setuptools python3-wheel
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

branch="main"

if [ "$0" == "--pre-release" ]; then
    branch="pre-release"
fi

echo "Selected branch: $branch"

if [ -d "$install_dir" ]; then
  echo "Directory $install_dir exists."
else
  git clone -b "$branch" "$repository_url" "$install_dir" || display_error_and_exit "Failed to clone the repository."
fi

cd "$install_dir" || display_error_and_exit "Failed to change directory."

echo -e "${GREEN}Step 2: Installing requirements...${RESET}"

# ایجاد محیط مجازی
VENV_DIR="$install_dir/venv"
python3 -m venv "$VENV_DIR" || display_error_and_exit "Failed to create virtual environment."

# فعال‌سازی محیط مجازی
source "$VENV_DIR/bin/activate" || display_error_and_exit "Failed to activate virtual environment."

# نصب pip به‌روز
python3 -m pip install --upgrade pip

# نصب setuptools و wheel
python3 -m pip install --upgrade setuptools wheel

# نصب پکیج‌های سیستم مورد نیاز
if [ -f /etc/os-release ]; then
  source /etc/os-release
  if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
    sudo apt update
    sudo apt install -y python3-dev build-essential libffi-dev
  elif [ "$ID" == "centos" ] || [ "$ID" == "rhel" ]; then
    sudo yum install -y python3-devel gcc libffi-devel
  fi
fi

# نصب پکیج‌ها با استفاده از python3 -m pip
python3 -m pip install --no-cache-dir -r requirements.txt || display_error_and_exit "Failed to install requirements."

# اطمینان از نصب requests
python3 -m pip install --no-cache-dir requests || display_error_and_exit "Failed to install requests."

echo -e "${GREEN}Step 3: Preparing ...${RESET}"
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

echo -e "${GREEN}Step 4: Running config.py to generate config.json...${RESET}"
"$VENV_DIR/bin/python3" config.py || display_error_and_exit "Failed to run config.py."

# ربات را با سرویس systemd راه‌اندازی می‌کند
setup_systemd_service() {
  echo "Creating systemd service for the bot..."
  
  # Create systemd service file
  cat > /etc/systemd/system/hiddify-telegram-bot.service << EOL
[Unit]
Description=Hiddify Telegram Bot Service
After=network.target

[Service]
User=root
WorkingDirectory=${install_dir}
ExecStart=${install_dir}/venv/bin/python ${install_dir}/hiddifyTelegramBot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

  # Reload systemd, enable and start the service
  systemctl daemon-reload
  systemctl enable hiddify-telegram-bot
  systemctl restart hiddify-telegram-bot
  
  echo "Systemd service created and started"
}

# تابع برای اضافه کردن cron jobs
add_cron_job() {
  echo "Adding cron jobs..."
  
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
  add_cron_job_if_not_exists "@reboot cd $install_dir && $VENV_DIR/bin/python $install_dir/hiddifyTelegramBot.py >>$install_dir/bot.log 2>&1 &"
  
  # Add cron job to run every 6 hours
  add_cron_job_if_not_exists "0 */6 * * * cd $install_dir && $VENV_DIR/bin/python $install_dir/crontab.py --backup >>$install_dir/cron.log 2>&1"
  
  # Add cron job to run at 12:00 PM daily
  add_cron_job_if_not_exists "0 12 * * * cd $install_dir && $VENV_DIR/bin/python $install_dir/crontab.py --reminder >>$install_dir/cron.log 2>&1"
  
  echo "Cron jobs added successfully"
}

# بعد از نصب سرویس را اضافه می‌کند
finalize_installation() {
  echo "Step 5: Running the bot in the background..."
  setup_systemd_service
  
  echo "Step 6: Adding cron jobs..."
  add_cron_job
  
  echo "Waiting for a few seconds..."
  sleep 3
  
  # Check service status
  service_status=$(systemctl is-active hiddify-telegram-bot)
  if [[ "$service_status" == "active" ]]; then
    echo "The bot has been started successfully."
    echo "Send [/start] in Telegram bot."
  else
    echo "WARNING: The bot service is not running properly."
    echo "Check the logs with: journalctl -u hiddify-telegram-bot -f"
  fi
}

# در انتهای اسکریپت
finalize_installation
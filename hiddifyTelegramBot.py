from threading import Thread
import AdminBot.bot
from config import CLIENT_TOKEN
import os
import sys
import logging
from termcolor import colored

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler()
    ]
)

# Start the admin bot
if __name__ == '__main__':
    print(colored("Starting Hiddify Telegram Bot...", "green"))
    print(colored(f"Current working directory: {os.getcwd()}", "cyan"))
    print(colored(f"Python version: {sys.version}", "cyan"))
    
    print(colored("Starting Admin Bot...", "yellow"))
    try:
        admin_thread = Thread(target=AdminBot.bot.start)
        admin_thread.daemon = True
        admin_thread.start()
        print(colored("Admin Bot started successfully!", "green"))
    except Exception as e:
        print(colored(f"Error starting Admin Bot: {e}", "red"))
        logging.error(f"Error starting Admin Bot: {e}")
    
    # Start the user bot if the client token is set
    if CLIENT_TOKEN:
        print(colored("Client token found. Starting User Bot...", "yellow"))
        try:
            import UserBot.bot
            user_thread = Thread(target=UserBot.bot.start)
            user_thread.daemon = True
            user_thread.start()
            print(colored("User Bot started successfully!", "green"))
        except Exception as e:
            print(colored(f"Error starting User Bot: {e}", "red"))
            logging.error(f"Error starting User Bot: {e}")
    else:
        print(colored("No client token found. User Bot will not be started.", "yellow"))
    
    print(colored("All bots have been started. Press Ctrl+C to exit.", "green"))
    
    # Keep the main thread alive
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(colored("Stopping bots...", "yellow"))
        sys.exit(0)


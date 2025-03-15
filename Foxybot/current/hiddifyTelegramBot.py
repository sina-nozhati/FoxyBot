from threading import Thread
import AdminBot.bot

# Start the admin bot
if __name__ == '__main__':
    Thread(target=AdminBot.bot.bot.polling, kwargs={'none_stop': True}).start()


from main_programm import *
import requests
import sys
import traceback

USE_WEBHOOK = True
APP_URL = 'https://whispering-depths-18963.herokuapp.com'
PORT = int(os.environ.get('PORT', '8443'))
BOT_TOKEN = os.environ.get('BOT_TOKEN')


def run_notification_thread():
    for thread in threading.enumerate():
        if 'notifier_thread' in thread.name:
            return

    notifier_thread = threading.Thread(target=push_notifications, args=(), name='notifier_thread')
    notifier_thread.start()
    return


def main():
    run_notification_thread()

    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('schedule', schedule_command))
    dispatcher.add_handler(CommandHandler('activities', activities_command))
    dispatcher.add_handler(CommandHandler('reset', reset_command))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('register', register_command))

    # admin
    dispatcher.add_handler(CommandHandler('register_requests', register_requests))
    dispatcher.add_handler(CommandHandler('allowed_users', allowed_users))
    dispatcher.add_handler(CommandHandler('blocked_users', blocked_users))

    dispatcher.add_handler(MessageHandler(Filters.text, text_handler))
    dispatcher.add_handler(CallbackQueryHandler(inline_button_handler))

    if not USE_WEBHOOK:
        # start using long polling
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        result = response.json()
        if result:
            if result.get('ok'):
                print('Webhook was removed!')
        updater.start_polling()
    else:
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        result = response.json()
        if result:
            if result.get('ok'):
                print('Webhook was removed!')

                response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={APP_URL}/{BOT_TOKEN}")
                result = response.json()
                if result.get('ok'):
                    print('Webhook was set!')

        updater.start_webhook(listen='0.0.0.0',
                                port=PORT,
                                url_path=BOT_TOKEN,
                                webhook_url=f'{APP_URL}/{BOT_TOKEN}')
        
    updater.idle()


if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            print(str(e))
            time.sleep(60)
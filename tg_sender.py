import os
import sys
import locale
from datetime import datetime, timedelta
import telegram

import start

# Задаем локаль для вывода даты на UKR языке в зависимости какая ОС
if sys.platform == 'linux':
    locale.setlocale(locale.LC_ALL, "uk_UA.utf8")  # Ubuntu
elif sys.platform == 'win32':
    locale.setlocale(locale.LC_ALL, "ukr")  # Windows
else:
    locale.setlocale(locale.LC_ALL, "uk_UA.UTF-8")  # Mac OS

token_bot = os.environ['TOKEN_BOT']  # Токен ТГ бота
bot = telegram.Bot(token=token_bot)  # для работы api бота
chat_id = os.environ['CHAT_ID']  # Чат, канал в Telegram

start.logging.info('Отправка в Телеграм канал...')


def send_to_telegram():
    """ Отправляет постеры с рейтнингом в телеграм"""
    # Активность: Пишет текст
    bot.sendChatAction(chat_id=chat_id, action=telegram.ChatAction.TYPING)

    description = datetime.strftime(datetime.now() - timedelta(weeks=1), 'Підсумок %W-го бігового тижня, %Y року (%B)')
    tag_month = datetime.strftime(datetime.now() - timedelta(weeks=1), '%B')
    media_group = [
        telegram.InputMediaPhoto(
            open(os.path.join(os.path.dirname(__file__), f'images/out/out{num}.png'), 'rb'), parse_mode='html',
            caption=f"📊 <b>{description}</b>\n\n"
                    f"#{tag_month} | #leaders_last_week | <a href='{start.URL}'>StravaClub</a>"
            if num == 1 else ''
        )
        for num in range(1, 3)
    ]
    bot.sendMediaGroup(chat_id=chat_id, media=media_group)
    start.logging.info('Постеры успешно отправлены.')

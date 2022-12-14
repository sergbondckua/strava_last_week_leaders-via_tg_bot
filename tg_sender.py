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
elif sys.platform == 'darwin':
    locale.setlocale(locale.LC_ALL, "uk_UA.UTF-8")  # MacOS

token_bot = os.getenv("TOKEN_BOT")  # Токен ТГ бота
bot = telegram.Bot(token=token_bot)  # для работы api бота
chat_id = os.getenv('CHAT_ID')  # Чат, канал в Telegram


def send_to_telegram():
    """ Отправляет постеры с рейтнингом в телеграм"""

    start.logging.info('Отправка в Телеграм канал...')
    # Активность: Пишет текст
    bot.sendChatAction(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    description = (datetime.now() - timedelta(weeks=1)).strftime('Підсумок %W-го бігового тижня, %Y року (%B)')
    tag_month = (datetime.now() - timedelta(weeks=1)).strftime('%B')
    media_group = [
        telegram.InputMediaPhoto(
            open(os.path.join(start.BASE_DIR, f'images/out/out{num}.png'), 'rb'), parse_mode='html',
            caption=f"📊 <b>{description}</b>\n\n"
                    f"#{tag_month} | #leaders_last_week | <a href='{start.URL}'>StravaClub</a>"
            if num == 1 else ''
        )
        for num in range(1, 3)
    ]
    bot.sendMediaGroup(chat_id=chat_id, media=media_group)
    start.logging.info('Постеры успешно отправлены.')

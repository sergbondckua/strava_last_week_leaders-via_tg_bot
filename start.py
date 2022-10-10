import os
import sys
import pickle
import time
from urllib.request import urlopen
from pathlib import Path
import logging

# Selenium modules
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from fake_user_agent import user_agent

# Включить ведение журнала логов
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути внутри проекта следующим образом: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


def get_source_html_page(url):
    """ Открывает сайт url Strava, авторизируется, переходит на страницу лидеров прошлой недели и сохраняет ее в html"""

    # Путь до chromedriver в зависимости какая ОС
    if sys.platform == 'linux':
        chromedriver = os.path.join(BASE_DIR, 'drivers/chromedriver')  # Linux
    elif sys.platform == 'win32':
        chromedriver = os.path.join(BASE_DIR, 'drivers/chromedriver.exe').replace('/', '\\')  # Windows
    else:
        chromedriver = os.path.join(BASE_DIR, 'drivers/chromedriver_mac')  # Mac OS

    useragent = user_agent('chrome')  # Фейковый юзер-агента брузера
    service = Service(chromedriver)  # Сервисы для webdriver
    options = Options()  # Опции для webdriver
    options.add_argument(f'user-agent={useragent}')  # Передаем аргумент юзерагент браузера
    options.add_argument('--disable-blink-features=AutomationControlled')  # Откл возможность определять сайтами webdriv
    options.headless = False  # Открывать браузер в фотоновом режиме
    options.add_argument('--no-sandbox')  # Отключает изолированную среду
    browser = Chrome(service=service, options=options)  # Создаем объект драйвера

    try:
        browser.get(url)
        if not os.path.isfile(os.path.join(BASE_DIR, 'source/auth_cookie')):
            browser.find_element(By.CLASS_NAME, 'btn-accept-cookie-banner').click()
            browser.find_element(By.CLASS_NAME, 'btn-login').click()

            # Авторизация
            logging.info('Открыта страница авторизации.')

            # Вводим email
            email_input = browser.find_element(By.ID, 'email')
            email_input.clear()
            email_input.send_keys(os.environ['EMAIL'])

            # Вводим password
            paswd_input = browser.find_element(By.ID, 'password')
            paswd_input.clear()
            paswd_input.send_keys(os.environ['PASSWD'])

            # Нажимаем на кнопку авторизации
            browser.find_element(By.ID, 'login-button').click()

            # Получаем coockies с сайта и сохраняем их в файл
            pickle.dump(browser.get_cookies(), open(os.path.join(BASE_DIR, 'source/auth_cookie'), 'wb'))
            logging.info('Авторизация успешна, файл с cookies сохранен.')

        # Достаем файл cookie и применям его для авторизации
        for cookie in pickle.load(open(os.path.join(BASE_DIR, 'source/auth_cookie'), 'rb')):
            browser.add_cookie(cookie)

        logging.info('Авторизация успешна!')

        # Нажимаем на кнопку показ таблицы лидеров прошлой недели
        browser.find_element(By.CLASS_NAME, 'last-week').click()
        logging.info('Переход к таблице лидеров прошлой недели')
        time.sleep(1)

        # Сохраняем HTML страницы  в файл
        with open(os.path.join(BASE_DIR, 'source/source-page.html'), 'w', encoding='utf-8') as file:
            file.write(browser.page_source)
        logging.info('Файл HTML всей страницы сохранен!')
    except Exception as ex:
        logging.exception(ex)
    finally:
        browser.close()
        browser.quit()


if __name__ == "__main__":
    get_source_html_page('https://www.strava.com/clubs/582642')

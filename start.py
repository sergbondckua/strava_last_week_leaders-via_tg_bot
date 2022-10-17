import os
import pickle
import time
from pathlib import Path
import logging
import pytz

# Selenium modules
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Подключаем менеджер драйвера Хрома
from webdriver_manager.chrome import ChromeDriverManager

from fake_user_agent import user_agent
from bs4 import BeautifulSoup
from apscheduler.schedulers.blocking import BlockingScheduler

# Custom
import pictools
import tg_sender

# Включить ведение журнала логов
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути внутри проекта следующим образом: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

# URL Strava Club для извлечения табл. лидеров прошедшей недели
URL = 'https://www.strava.com/clubs/582642'


def get_source_html_page(url):
    """ Открывает сайт url Strava, авторизируется,
    переходит на страницу лидеров прошлой недели и сохраняет ее в HTML
    """

    # Здесь менеджер драйвера Хрома проверит версии и установит нужную (актуальную).
    chromedriver = ChromeDriverManager().install()

    useragent = user_agent('chrome')  # Фейковый юзер-агента брузера
    service = Service(chromedriver)  # Сервисы для webdriver
    options = Options()  # Опции для webdriver
    options.add_argument(f'user-agent={useragent}')  # Передаем аргумент юзерагент браузера
    options.add_argument(
        '--disable-blink-features=AutomationControlled')  # Откл возможность определять сайтами webdriv
    options.headless = True  # Открывать браузер в фотоновом режиме
    options.add_argument('--no-sandbox')  # Отключает изолированную среду
    browser = Chrome(service=service, options=options)  # Создаем объект драйвера

    try:
        if not os.path.isfile(os.path.join(BASE_DIR, 'source/auth_cookie')):
            browser.get('https://www.strava.com/login')
            browser.find_element(By.CLASS_NAME, 'btn-accept-cookie-banner').click()

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
            pickle.dump(browser.get_cookies(),
                        open(os.path.join(BASE_DIR, 'source/auth_cookie'), 'wb'))
            logging.info('Авторизация, файл с cookies сохранен.')
            browser.get(url)
        else:
            browser.get(url)
            # Достаем файл cookie и применям его для авторизации
            for cookie in pickle.load(open(os.path.join(BASE_DIR, 'source/auth_cookie'), 'rb')):
                browser.add_cookie(cookie)
            # Обязательно обновляем, чтобы cookies применились
            browser.refresh()
            logging.info('Авторизация успешна!')

        # Нажимаем на кнопку показ таблицы лидеров прошлой недели
        browser.find_element(By.CLASS_NAME, 'last-week').click()
        logging.info('Переход к таблице лидеров прошлой недели')
        time.sleep(1)

        # Забираем данные из таблицы лидеров
        try:
            WebDriverWait(browser, 10).until(
                ec.presence_of_element_located((By.CLASS_NAME, 'dense')))
        except TimeoutException as e:
            logging.exception(e)

        last_week_leaders = []
        lst = []

        table = browser.find_element(By.CLASS_NAME, 'dense')
        tr_contents = table.find_elements(By.TAG_NAME, 'tr')

        for num, tr in enumerate(tr_contents[1:]):
            athlete_url = tr.find_element(By.TAG_NAME, 'a').get_attribute('href').strip()
            avatar_medium = tr.find_element(By.TAG_NAME, 'img').get_attribute('src').strip()
            avatar_large = tr.find_element(By.TAG_NAME, 'img').get_attribute(
                'src').strip().replace('medium', 'large')

            # Проходим, чтобы найти td под каждым tr
            for td in tr.find_elements(By.TAG_NAME, 'td'):
                # Сохраняем содержимое каждого td в lst
                lst.append(td.text)

            # Формируем список словарей с данными спортсмена из табл.
            last_week_leaders.append(dict(zip(
                ['rank', 'athlete_name', 'distance', 'activities',
                 'longest', 'avg_pace', 'elev_gain'], lst)))

            last_week_leaders[num]['avatar_large'] = avatar_large
            last_week_leaders[num]['avatar_medium'] = avatar_medium
            last_week_leaders[num]['link'] = athlete_url
            lst = []

        logging.info(
            f"Сформирован список словарей с данными спортсмена из таблицы")

        return last_week_leaders
    except Exception as ex:
        logging.exception(ex)
    finally:
        browser.close()
        browser.quit()


def main():
    pictools.get_poster_leaders(get_source_html_page(URL))
    tg_sender.send_to_telegram()


if __name__ == "__main__":
    # Планировщик запуска
    sched = BlockingScheduler(timezone=pytz.timezone("Europe/Kiev"))

    # Каждый понедельник в 12:00
    sched.add_job(main, 'cron', day_of_week='mon', hour='12', minute="00")

    # Запуск daemon
    sched.start()

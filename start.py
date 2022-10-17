import os
import pickle
import time
from pathlib import Path
import logging
import pytz

# Selenium modules
from selenium.webdriver.common.by import By
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
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
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
    options.add_argument('--disable-blink-features=AutomationControlled')  # Откл возможность определять сайтами webdriv
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
            pickle.dump(browser.get_cookies(), open(os.path.join(BASE_DIR, 'source/auth_cookie'), 'wb'))
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

        # Сохраняем HTML страницы  в файл
        with open(os.path.join(BASE_DIR, 'source/source-page.html'), 'w', encoding='utf-8') as file:
            file.write(browser.page_source)
        logging.info(f"Файл HTML всей страницы сохранен! [{os.path.join(BASE_DIR, 'source/source-page.html')}]")
    except Exception as ex:
        logging.exception(ex)
    finally:
        browser.close()
        browser.quit()


def get_leaders_data_list(file_path=os.path.join(BASE_DIR, 'source/source-page.html')):
    """ Возвращает список словарей со всемы данными о спортсмене и его результаты """

    with open(file_path, encoding='utf-8') as f:
        src = f.read()

    soup = BeautifulSoup(src, 'lxml')

    # Забираем данные из таблицы рейтинга спортсменов
    items_table = soup.find('table', class_='dense').find_all('tr')
    week_leaders = []

    for item in items_table[1:]:
        rank = item.find('td', class_='rank').text.strip()
        athlete_name = item.find('a', class_='athlete-name').text.strip()
        athlete_url = 'https://www.strava.com' + item.find('a', class_='athlete-name').get('href').strip()
        avatar_large = item.find('img').get('src').strip().replace('medium', 'large')
        avatar_medium = item.find('img').get('src').strip()
        distance = item.find('td', class_='distance').text.strip()
        num_activities = item.find('td', class_='num-activities').text.strip()
        longest_activity = item.find('td', class_='longest-activity').text.strip()
        average_pace = item.find('td', class_='average-pace').text.strip()
        elev_gain = item.find('td', class_='elev-gain').text.strip()

        week_leaders.append(dict(
            rank=rank,
            name=athlete_name,
            link=athlete_url,
            avatar_large=avatar_large,
            avatar_medium=avatar_medium,
            distance=distance,
            activities=num_activities,
            longest=longest_activity,
            avg_pace=average_pace,
            elev_gain=elev_gain
        ))
    logging.info('Рейтинг спортсменов клуба прошедшей недели составлен!')
    # Удаляем файл, как неактуальный
    if os.path.isfile(os.path.join(BASE_DIR, 'source/source-page.html')):
        os.remove(os.path.join(BASE_DIR, 'source/source-page.html'))
    return week_leaders


def main():
    get_source_html_page(URL)
    pictools.get_poster_leaders(get_leaders_data_list())
    tg_sender.send_to_telegram()


if __name__ == "__main__":
    # Планировщик запуска
    sched = BlockingScheduler(timezone=pytz.timezone("Europe/Kiev"))

    # Каждый понедельник в 12:00
    sched.add_job(main, 'cron', day_of_week='mon', hour='12', minute="00")

    sched.start()

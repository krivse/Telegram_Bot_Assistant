import telegram
import requests
import os
from dotenv import load_dotenv
import time
from exceptions import TokenErrorException
import logging
import sys

load_dotenv()
PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('T_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = ''
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger()
fileHandler = logging.FileHandler("logfile.log")
streamHandler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)


def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.info(f'Бот отправил сообщение: {message}')


def get_api_answer(current_timestamp):
    """API запрос с преобразованием в JSON формат"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        ENDPOINT, headers=HEADERS, params=params)
    return response.json()


def check_response(response):
    """Проверка API на корректность, возвращение списка по ключу."""
    homework = response.get('homeworks')
    return homework


def parse_status(homework):
    """Получение статуса домашней работы"""
    if homework != []:
        homework_name = homework[0].get('homework_name')
        homework_status = homework[0].get('status')
        if homework_status in HOMEWORK_STATUSES.keys():
            verdict = HOMEWORK_STATUSES.get(homework_status)
            return logger.info(f'Изменился статус проверки работы'
                               f'"{homework_name}". {verdict}')
    elif homework == []:
        return logger.info('Успешный запрос, но обновлений пока нет')


def check_tokens():
    """Проверка доступности ключей."""
    if (TELEGRAM_CHAT_ID is None
       or PRACTICUM_TOKEN is None
       or TELEGRAM_TOKEN is None):
        return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is not True:
        raise logger.critical(TokenErrorException(
            'Хранилище ключей недоступно / ключ недоступен. '
            'Программа принудительно остановлена'))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            response = send_message(bot, message)
            logger.error(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)
        else:
            pass


if __name__ == '__main__':
    main()

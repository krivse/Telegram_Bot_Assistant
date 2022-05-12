from http import HTTPStatus
import telegram
import requests
import os
from dotenv import load_dotenv
import time
from exceptions import APIException, JSONException, ParsingException
from exceptions import TokenException
import logging
import sys

load_dotenv()
PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('T_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger()
fileHandler = logging.FileHandler("logfile.log")
streamHandler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '- %(levelname)s - %(funcName)s - %(lineno)s - %(asctime)s - %(message)s')
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)


def send_message(bot, message):
    """Отправка БОТОМ любого сообщения"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение: {message}')
    except telegram.error.TelegramError as error:
        logger.error(f'Сообщение не было отправлено: {error}')
        raise (f'Сообщение не было отправлено: {error}')


def get_api_answer(current_timestamp):
    """API запрос с преобразованием в JSON формат."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        logger.info(f'Успешный запрос к API: {response.status_code}')
        return response.json()
    else:
        logger.error(f'Неуспешный запрос с API: {response.status_code}')
        raise APIException(f'Неуспешный запрос к API: {response.status_code}')


def check_response(response):
    """Проверка API на корректность, возвращение списка по ключу."""
    if isinstance(response, dict):
        logger.info(
            f'JSON формат имеет правильный тип данных: {type(response)}')
        homework = response.get('homeworks')
        if isinstance(homework, list):
            logger.info(
                f'Правильное значение ключа словаря "list": {type(homework)}')
            return homework
        else:
            logger.error(
                f'Ожидается тип данных "list": {type(homework)}')
            raise JSONException(
                f'Ожидается тип данных "list": {type(homework)}')
    elif response is None:
        logger.error(f'Ответ от API пустой: {response}')
    elif not isinstance(response, dict):
        logger.error(
            f'JSON формат имеет неправильный тип данных: {type(response)}')
        raise TypeError(
            f'JSON формат имеет неправильный тип данных: {type(response)}')


def parse_status(homework):
    """Получение имя / статус домашней работы."""
    if homework != []:
        if 'homework_name' not in homework.keys():
            raise KeyError('Нет ключа: "homework_name"')
        elif 'status' not in homework.keys():
            raise KeyError('Нет ключа: "status"')
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status in HOMEWORK_STATUSES.keys():
            verdict = HOMEWORK_STATUSES.get(homework_status)
            logger.info(
                f'Изменился статус проверки работы: {verdict}')
            return (
                f'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}')
        elif homework_status not in HOMEWORK_STATUSES.keys():
            logger.error(
                f'Недокументированный статус работы: {homework_status}'
            )
            raise ParsingException(
                f'Недокументированный статус работы: {homework_status}'
            )
    elif homework == []:
        logger.info(
            'Успешный запрос, но статус домашней работы не получил обновления')
        return (
            'Успешный запрос, но статус домашней работы не получил обновления')
    else:
        logger.error(
            f'Недокументрированный формат запроса {homework}.'
        )


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
        raise logger.critical(TokenException(
            'Хранилище ключей недоступно / ключ недоступен. '
            'Программа принудительно остановлена'))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            send_message(bot, message)
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            response = send_message(bot, message)
            logger.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

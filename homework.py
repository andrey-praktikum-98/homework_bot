import logging
import os
import sys
import time
import json
from logging import StreamHandler
from http import HTTPStatus


import requests
from dotenv import load_dotenv
from telegram import TelegramError
from telegram import Bot


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение со статусом проверки работы в Телеграм чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info(f'Бот отправил сообщение "{message}"')
    except TelegramError as error:
        logger.error(
            f'При отправке сообщения "{message}" возникла ошибка "{error}".'
        )
    except Exception as error:
        logger.error(
            f'При отправке сообщения "{message}" возникла ошибка "{error}".'
        )


def get_api_answer(current_timestamp):
    """Запрос к API, ответ, приведенный к типам данных Python."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        logger.error(f'Сервис недоступен, ошибка {e}')
        raise SystemExit('Сервис недоступен')
    if response.status_code != HTTPStatus.OK:
        logger.error(
            f'При запросе к эндпоинту'
            f'вернулся код ответа {response.status_code}')
        raise requests.ConnectionError(
            f'При запросе к эндпоинту'
            f'вернулся код ответа {response.status_code}')
    try:
        response_api = response.json()
    except json.decoder.JSONDecodeError as e:
        logger.error(f'Сервис недоступен, ошибка {e}')
    return response_api


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        logger.error('Ответ не в формате dict')
        raise TypeError('Ответ не в формате dict')
    if not response.get('homeworks'):
        logger.error('Отсутствует ключ "homeworks"')
        raise KeyError('Отсутствует ключ "homeworks"')
    homework = response.get('homeworks')
    if not type(homework) is list:
        logger.error('Список работ не в формате list')
        raise KeyError('Список работ не в формате list')
    return homework


def parse_status(homework):
    """Извлекает статус проверки работы, возвращает текст сообщения."""
    if homework.get('homework_name') is None:
        logger.error('Отсутствует ключ "homework_name"')
        raise KeyError('Отсутствует ключ "homework_name"')
    homework_name = homework.get('homework_name')
    if not homework.get('status'):
        logger.error('Отсутствует ключ "status"')
        raise KeyError('Отсутствует ключ "status"')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Неизвестный статус проверки работы')
        raise KeyError('Неизвестный статус проверки работы')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка на наличие токенов."""
    tokens = True
    if not PRACTICUM_TOKEN:
        logger.critical(
            'Отсутствует переменная окружения PRACTICUM_TOKEN'
        )
        tokens = False
    if not TELEGRAM_TOKEN:
        logger.critical(
            'Отсутствует переменная окружения TELEGRAM_TOKEN'
        )
        tokens = False
    if not TELEGRAM_CHAT_ID:
        logger.critical(
            'Отсутствует переменная окружения TELEGRAM_CHAT_ID'
        )
        tokens = False
    return tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.error('Проверка токена передает пустое значение')
        return None
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message = ''
    prev_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks is not None:
                message = parse_status(homeworks[0])
                current_timestamp = response.get(
                    'current_date',
                    current_timestamp)
                send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            if message != prev_message:
                send_message(bot, message)


if __name__ == '__main__':
    main()

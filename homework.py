import logging
import os
import sys
import time
from logging import StreamHandler
from pytest import Instance

import requests
from dotenv import load_dotenv
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
    except Exception as error:
        logger.error(
            f'При отправке сообщения "{message}" возникла ошибка "{error}".'
        )


def get_api_answer(current_timestamp):
    """Запрос к API, ответ, приведенный к типам данных Python."""
    params = {'from_date': current_timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logger.error(
            f'При запросе к эндпоинту вернулся код ответа \
            {response.status_code}'
        )
        raise requests.ConnectionError(
            f'При запросе к эндпоинту вернулся код ответа \
            {response.status_code}')
    return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        logger.error('Ответ не в формате dict')
        raise TypeError('Ответ не в формате dict')
    if not type(response.get('homeworks')) is list:
        logger.error('Список работ не в формате list')
        raise KeyError('Список работ не в формате list')
    elif not response.get('homeworks'):
        logger.error('Отсутствует ключ "homeworks"')
        raise KeyError('Отсутствует ключ "homeworks"')
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает статус проверки работы, возвращает текст сообщения."""
    homework_name = homework.get('homework_name')
    if not homework.get('status'):
        logger.error('Отсутствует ключ "status"')
        raise KeyError('Отсутствует ключ "status"')
    if homework.get('status') not in HOMEWORK_STATUSES:
        logger.error('Неизвестный статус проверки работы')
        raise KeyError('Неизвестный статус проверки работы')
    homework_status = homework.get('status')
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
        return None
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(0)
    message = ''
    prev_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks is not None:
                message = parse_status(homeworks[0])
                current_timestamp = response.get('current_timestamp')
                print(message)
                send_message(bot, message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)

        else:
            if message != prev_message:
                send_message(bot, message)
                message = prev_message


if __name__ == '__main__':
    main()

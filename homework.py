import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiAnswerError, BotMessageError, ParseStatusError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    list_env = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    for token in list_env:
        if token is None:
            logging.critical(
                'Отсутствует обязательная переменная окружения: '
                f'{token}!')
    return all(list_env)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено!')
    except Exception:
        logging.error('Отправка сообщения невозможна!')
        raise BotMessageError('Отправка сообщения невозможна!')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise ApiAnswerError(
                f'Некорректный статус код:{homework_statuses.status_code}')
        logging.debug(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
        return homework_statuses.json()
    except requests.exceptions.RequestException as request_error:
        logging.error(f'Ошибка запроса {request_error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('В функцию "check_response" поступил не словарь')
        raise TypeError('В функцию "check_response" поступил не словарь')
    if 'homeworks' not in response:
        logging.error('Ключ homeworks отсутствует')
        raise KeyError('Ключ homeworks отсутствует')
    if not isinstance(response['homeworks'], list):
        logging.error('Объект homeworks не является списком')
        raise TypeError('Объект homeworks не является списком')
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы"""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует в homework')
    if 'status' not in homework:
        message = 'Отсутстует ключ homework_status.'
        logging.error(message)
        raise ParseStatusError(message)
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status is None:
        logging.debug('Статус домашних работ не изменился.')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('homework_status отсутствует в HOMEWORK_VERDICTS')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.\n'
            'Программа принудительно остановлена.'
        )
        sys.exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 30 * 24 * 60 * 60
    previous_homework = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks and homeworks != previous_homework:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                logging.info(f'Бот отправил сообщение: "{message}"')
                previous_homework = homeworks
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Ошибка при запросе к основному API: {error}')
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

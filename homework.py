import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=logging.StreamHandler(sys.stdout)
)


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


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logging.error('Упс, не доступно!')
        raise Exception('Упс, не доступно!')
    response = response.json()
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        logging.error('Должен быть словарь.')
        raise TypeError('Должен быть словарь.')
    if not isinstance(response.get('homeworks'), list):
        logging.error('Должен быть список.')
        raise TypeError('Должен быть список.')
    if 'current_date' not in response.keys():
        logging.error('Не хватает ключа current_date.')
        raise TypeError('Не хватает ключа current_date.')
    if 'homeworks' not in response.keys():
        logging.error('Не хватает ключа homeworks.')
        raise TypeError('Не хватает ключа homeworks.')
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError:
        logging.error('Осутствует ключ homework_name.')
    try:
        homework_status = homework.get('status')
    except KeyError:
        logging.error('Отсутствует ключ syatus.')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        logging.error('Статус не существует.')
        raise KeyError('Статус не существует.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    list_token = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in list_token:
        if token is None:
            logging.critical(
                f'Отсутствует {token}.Конец работы.'
            )
            return False
    return True


def main():
    """Основная логика работы бота."""
    logging.debug('Бот запущен')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    print(current_timestamp)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                logging.info('Сообщение отправлено.')
                current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            time.sleep(5.0)


if __name__ == '__main__':
    main()

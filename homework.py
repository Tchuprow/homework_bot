import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('main.log'),
        logging.StreamHandler(sys.stdout)
    ]
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


def send_message(bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError:
        raise exceptions.NotSendMessageError(
            'Сообщение не отправлено.'
        )


def get_api_answer(current_timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp: int = current_timestamp or int(time.time())
    params: dict = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except exceptions.NotSendMessageError():
        raise exceptions.NotSendMessageError(
            'Запрос к API не выполнен.'
        )
    if response.status_code != HTTPStatus.OK:
        raise Exception('Эндпоинт API-сервиса не доступен!')
    response: dict = response.json()
    return response


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Должен быть словарь.')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Должен быть список.')
    if 'current_date' not in response.keys():
        raise TypeError('Не хватает ключа current_date.')
    return homeworks


def parse_status(homework: list) -> str:
    """Извлекает из информации о конкретной домашней работе статус работы."""
    homework_name: str = homework.get('homework_name')
    try:
        homework_status: str = homework['status']
    except KeyError:
        raise exceptions.NotSendMessageError(
            'Не обнаружен ключ status.'
        )
    verdict: str = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise KeyError(f'Статус {homework_status} не существует.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    logging.info('Бот запущен')
    if not check_tokens():
        logging.critical('Отсутствует токен.Конец работы!')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp: int = int(time.time())
    while True:
        try:
            logging.info('Выполняем запрос к API.')
            response: dict = get_api_answer(current_timestamp)
            homeworks: list = check_response(response)
            if homeworks:
                message: str = parse_status(homeworks[0])
                logging.debug('Изменение статуса не обнаружено.')
                send_message(bot, message)
                logging.info('Сообщение отправлено.')
            current_timestamp: int = response.get('current_date')
        except Exception as error:
            message: str = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        except exceptions.NotSendMessageError() as e:
            logging.error(f'Сбой в работе программы: {e}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

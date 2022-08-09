import exceptions
import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus

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
        logging.info('Начинаем отправлять сообщение.')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError:
        raise exceptions.NotSendMessageError(
            'Сообщение не отправлено.'
        )
    else:
        logging.info('Сообщение отправлено.')


def get_api_answer(current_timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp: int = current_timestamp or int(time.time())
    params: dict = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logging.error('Эндпоинт API-сервиса не доступен!')
            raise requests.ConnectionError(
                'Эндпоинт API-сервиса не доступен!'
            )
    except Exception:
        logging.error('Запрос к API не выполнен.')
        raise Exception('Запрос к API не выполнен.')
    response: dict = response.json()
    return response


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            'Значение response должно быть словарем.'
        )
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            'Значение homeworks должно быть списком.'
        )
    if 'current_date' not in response.keys():
        raise KeyError('Не хватает ключа current_date.')
    return homeworks


def parse_status(homework: list) -> str:
    """Извлекает из информации о конкретной домашней работе статус работы."""
    homework_name: str = homework.get('homework_name')
    try:
        homework_status: str = homework['status']
    except KeyError:
        raise KeyError(
            'Не обнаружен ключ status.'
        )
    verdict: str = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise KeyError(f'Статус {homework_status} не существует.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,))


def main():
    """Основная логика работы бота."""
    logging.info('Бот запущен')
    if not check_tokens():
        logging.critical('Отсутствует токен.Конец работы!')
        sys.exit('Отсутствует токен.Конец работы!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message: str = ''
    message_not_work: str = ''
    second_message_error: str = ''
    while True:
        try:
            logging.info('Выполняем запрос к API.')
            response: dict = get_api_answer(current_timestamp)
            homeworks: list = check_response(response)
            if homeworks:
                message: str = parse_status(homeworks[0])
                logging.debug('Изменение статуса не обнаружено.')
                send_message(bot, message)
            else:
                if message_not_work == message:
                    message_not_work: str = 'ДЗ нет.'
                    send_message(bot, message_not_work)
            current_timestamp: int = response.get('current_date')
        except exceptions.NotSendMessageError as e:
            logging.error(f'Сбой в работе программы: {e}')
        except Exception as error:
            first_message_error: str = f'Сбой в работе программы: {error}'
            if first_message_error != second_message_error:
                logging.error(first_message_error)
                send_message(bot, first_message_error)
                second_message_error = first_message_error
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

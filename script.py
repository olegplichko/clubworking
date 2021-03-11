import logging
import os
import random
from datetime import datetime, timedelta
from time import sleep

import requests
import yaml

BOT_TOKEN = os.environ.get('BOT_TOKEN')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
SCHEDULE_CHAT_ID = os.environ.get('SCHEDULE_CHAT_ID', 0)
CHAT_IDS = [SCHEDULE_CHAT_ID]
mode = os.environ.get('MODE', 'debug')
DEBUG = mode == 'debug'

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def debuggable(stop=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug('%s: %s %s', func.__name__, args, kwargs)
            if stop:
                return
            return func(*args, **kwargs)

        return wrapper

    return decorator


@debuggable(DEBUG)
def send_message(text):
    for chat_id in CHAT_IDS:
        response = requests.post(
            f'{TELEGRAM_API_URL}/sendMessage',
            data={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        )


@debuggable(DEBUG)
def wait(seconds):
    sleep(seconds)


def settime(hours_minutes_str=None, **kwargs):
    result = datetime.now()
    if hours_minutes_str:
        hours_minutes = datetime.strptime(hours_minutes_str, "%H:%M")
        result = result.replace(hour=hours_minutes.hour, minute=hours_minutes.minute)
    if kwargs:
        result = result.replace(**kwargs)
    return result


if __name__ == '__main__':
    with open('config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    skipped = True
    weekday = datetime.today().weekday()
    for item in config['data']:
        now = datetime.now()
        now = now.replace(microsecond=0)
        end_time = datetime.now()
        hours_minutes = datetime.strptime(item['stop'], "%H:%M")
        end_time = end_time.replace(hour=hours_minutes.hour, minute=hours_minutes.minute, second=0)
        if not skipped or 25 > (end_time - now).total_seconds() / 60 > 0:
            emoji = random.choice(item['emoji']) if isinstance(item['emoji'], list) else item['emoji']
            text = f"{emoji} <b>{item['start']} - {item['stop']}</b> <i>{item['description']}</i>"
            send_message(text)
        total_seconds = (end_time - now).total_seconds()
        delay = int(total_seconds)
        skipped = delay < 0
        if skipped:
            logger.debug('skipped %s', item)
            continue
        else:
            logger.debug('now: %s delay: %s alert time: %s', now, delay, now + timedelta(seconds=delay))
            wait(delay)

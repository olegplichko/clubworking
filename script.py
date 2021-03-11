import logging
import os
import random
from datetime import datetime, timedelta
from time import sleep

import requests
import yaml
import base64

BOT_TOKEN = os.environ.get('BOT_TOKEN')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
SCHEDULE_CHAT_ID = os.environ.get('SCHEDULE_CHAT_ID', 0)
CHAT_IDS = [SCHEDULE_CHAT_ID]
SPOTIFY_ACCESS_TOKEN = None
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REFRESH_TOKEN = os.environ.get('SPOTIFY_REFRESH_TOKEN')
CLIENT_CREDS = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
CLIENT_CREDS_B64 = base64.b64encode(CLIENT_CREDS.encode())

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


def run(config_path):
    with open(config_path) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    skipped = True
    n = len(config['data']) - 1
    for index, item in enumerate(config['data']):
        now = datetime.now()
        now = now.replace(microsecond=0)
        end_time = datetime.now()
        hours_minutes = datetime.strptime(item['stop'], "%H:%M")
        end_time = end_time.replace(hour=hours_minutes.hour, minute=hours_minutes.minute, second=0)
        if not skipped or 25 > (end_time - now).total_seconds() / 60 > 0:
            emoji = random.choice(item['emoji']) if isinstance(item['emoji'], list) else item['emoji']
            text = f"{emoji} <b>{item['start']} - {item['stop']}</b> <i>{item['description']}</i>"
            send_message(text)
            if item['status'] == 'B' or item['status'] == 'LB':
                access_token = refresh_spotify_token()
                play_spotify(access_token)
        total_seconds = (end_time - now).total_seconds()
        delay = int(total_seconds)
        skipped = delay < 0
        if skipped:
            logger.debug('skipped %s', item)
        else:
            logger.debug('now: %s delay: %s alert time: %s', now, delay, now + timedelta(seconds=delay))
            wait(delay)
        if index == n:
            for i in range(15):
                refresh_spotify_token()
                sleep(60 * 60)


def set_volume(volume, access_token):
    requests.put(
        f"https://api.spotify.com/v1/me/player/volume?volume_percent={volume}",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )


def refresh_spotify_token():
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            'grant_type': 'refresh_token',
            'refresh_token': SPOTIFY_REFRESH_TOKEN,
        },
        headers={
            "Authorization": f"Basic {CLIENT_CREDS_B64.decode()}"
        }
    )
    print(response.json())
    result = response.json()['access_token']
    with open('token', 'w') as f:
        f.write(result)
    return result


def play_spotify(access_token):
    volume = 10
    set_volume(volume, access_token)
    requests.put(
        "https://api.spotify.com/v1/me/player/play",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    for i in range(10):
        volume += 5
        set_volume(volume, access_token)
        sleep(5)


if __name__ == '__main__':
    run('config.yaml')

# https://github.com/sleleko/devops-kb
import requests
import json
import datetime
import pytz
from enum import Enum

URL = 'https://cozy.geigi.dev:3100/api/prom/push'

class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4

LOG_LEVEL_MAP = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.INFO: "INFO",
    LogLevel.WARNING: "WARN",
    LogLevel.ERROR: "ERROR"
}

def info():
    pass

def warning():
    pass

def error():
    pass

def exception():
    pass

def __report(component:str, type: LogLevel, message: str, exception: Exception):
    curr_datetime = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
    curr_datetime = curr_datetime.isoformat('T')

    if not component or not type or not message:
        raise ValueError("component, type and message are mandatory")

    labels = __append_label("", "component", component)
    labels =__append_label(labels, "message", message)

    if exception:
        labels = __append_label(labels, "exception_type", exception.__class__.__name__)

    # dist dist_version version

    line = "[{}] {}".format(LOG_LEVEL_MAP[type], message)

    headers = {
        'Content-type': 'application/json'
    }
    payload = {
        'streams': [
            {
                'labels': labels,
                'entries': [
                    {
                        'ts': curr_datetime,
                        'line': line
                    }
                ]
            }
        ]
    }
    payload = json.dumps(payload)
    response = requests.post(URL, data=payload, headers=headers)

def __append_label(labels, new_label_name, new_label_content):
    if labels:
        labels += ","
    else:
        labels = ""

    labels += "{}=\"{}\"".format(new_label_name, new_label_content)

    return labels

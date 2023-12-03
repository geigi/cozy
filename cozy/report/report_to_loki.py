import os

import requests
import datetime
import pytz
import distro
import platform

from cozy.application_settings import ApplicationSettings
from cozy.ext import inject
from cozy.report.log_level import LogLevel
from cozy.version import __version__ as CozyVersion
from peewee import __version__ as PeeweeVersion
from mutagen import version_string as MutagenVersion

from gi.repository import Gtk

URL = 'https://errors.cozy.sh:3100/api/prom/push'
ENABLE = '@INSTALLED@'

LOG_LEVEL_MAP = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.INFO: "INFO",
    LogLevel.WARNING: "WARN",
    LogLevel.ERROR: "ERROR"
}


def report(component: str, type: LogLevel, message: str, exception: Exception):
    if ENABLE != 'true':
        return

    app_settings = inject.instance(ApplicationSettings)
    report_level = app_settings.report_level

    if report_level == 0:
        return

    curr_datetime = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
    curr_datetime = curr_datetime.isoformat('T')

    if not component or not type or not message:
        raise ValueError("component, type and message are mandatory")

    labels = __append_label("", "component", component)

    if exception:
        labels = __append_label(labels, "exception_type", exception.__class__.__name__)

    labels = __append_label(labels, "app", "cozy")
    labels = __append_label(labels, "level", LOG_LEVEL_MAP[type])

    labels = __append_label(labels, "gtk_version", "{}.{}".format(Gtk.get_major_version(), Gtk.get_minor_version()))
    labels = __append_label(labels, "python_version", platform.python_version())
    labels = __append_label(labels, "peewee_version", PeeweeVersion)
    labels = __append_label(labels, "mutagen_version", MutagenVersion)
    labels = __append_label(labels, "version", CozyVersion)

    if report_level > 1:
        labels = __append_label(labels, "distro", distro.name())
        labels = __append_label(labels, "distro_version", distro.version())
        labels = __append_label(labels, "desktop_environment", os.environ.get('DESKTOP_SESSION'))

    line = "[{}] {}".format(LOG_LEVEL_MAP[type], message)

    headers = {
        'Content-type': 'application/json'
    }
    payload = {
        'streams': [
            {
                'labels': "{{{}}}".format(labels),
                'entries': [
                    {
                        'ts': curr_datetime,
                        'line': line
                    }
                ]
            }
        ]
    }
    try:
        requests.post(URL, json=payload, headers=headers, timeout=10)
    except:
        pass


def __append_label(labels, new_label_name, new_label_content):
    if labels:
        labels += ","
    else:
        labels = ""

    labels += "{}=\"{}\"".format(new_label_name, new_label_content)

    return labels

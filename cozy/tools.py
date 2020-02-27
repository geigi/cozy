from datetime import datetime
import time
import threading
from platform import system as get_system
from enum import Enum
from gettext import ngettext
import logging as log
import distro
from gi.repository import Gio
import cozy.magic.magic as magic

class Platform(Enum):
    Linux = 0
    Mac = 1

def system_platform():
    os = get_system().upper()
    if "LINUX" in os:
        return Platform.Linux
    else:
        return Platform.Mac


def shorten_string(string, length):
    """
    Shortens a string when it is longer than length and adds … at the end.
    :param string: Text to be shortened
    :param length: Max. length of string
    :return : string or shortened string
    """
    return (string[:length] + '…') if len(string) > length else string

def is_elementary():
        """
        Currently we are only checking for elementaryOS
        """
        dist = distro.linux_distribution(full_distribution_name=False)
        log.debug(dist)
        if '"elementary"' in dist or 'elementary' in dist:
            return True
        else:
            return False


settings = Gio.Settings.new("com.github.geigi.cozy")
def get_glib_settings():
    global settings
    return settings

# https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target=None):
        super(StoppableThread, self).__init__(target=target)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

# From https://stackoverflow.com/questions/11488877/periodically-execute-function-in-thread-in-real-time-every-n-seconds
class IntervalTimer(StoppableThread):

    def __init__(self, interval, worker_func):
        super().__init__()
        self._interval = interval
        self._worker_func = worker_func

    def run(self):
        while not self.stopped():
            self._worker_func()
            time.sleep(self._interval)


def seconds_to_str(seconds, include_seconds=True, display_zero_h=False):
    """
    Converts seconds to a string with the following apperance:
    hh:mm:ss

    :param seconds: The seconds as float
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if include_seconds:
        if (h > 0):
            result = "%d:%02d:%02d" % (h, m, s)
        elif (m > 0):
            result = "%02d:%02d" % (m, s)
            if display_zero_h:
                result = "0:" + result
        else:
            result = "00:%02d" % (s)
            if display_zero_h:
                result = "0:" + result
    else:
        if (h > 0):
            result = "%d:%02d" % (h, m)
        elif (m > 0):
            result = "00:%02d" % (m)
            if display_zero_h:
                result = "0:" + result
        else:
            result = "00:00"
            if display_zero_h:
                result = "0:" + result

    return result

def remove_all_children(container):
    """
    Removes all widgets from a gtk container.
    """
    container.set_visible(False)
    childs = container.get_children()
    for element in childs:
        container.remove(element)
        #element.destroy()
    container.set_visible(True)

def seconds_to_human_readable(seconds):
    """
    Create a string with the following format:
    6 hours 1 minute
    45 minutes
    21 seconds
    :param seconds: Integer
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    h = int(h)
    m = int(m)
    s = int(s)

    result = ""
    if h > 0:
        result += str(h) + " "
        if h > 1:
            result += _("hours")
        else:
            result += _("hour")
    
        if m > 0:
            result += " "

    if m > 0:
        result += str(m) + " "
        if m > 1:
            result += _("minutes")
        else:
            result += _("minute")
    
    if h < 1 and m < 1:
        if s < 1:
            result += _("finished")
        else:
            result += str(s) + " "
            if s > 1 or s < 1:
                result += _("seconds")
            else:
                result += _("second")

    return result

def past_date_to_human_readable(unix_time):
    """
    Converts the date to the following strings (from today):
    today
    yesterday
    x days ago
    x week(s) ago
    x month(s) ago
    x year(s) ago
    :param unix_time:
    """
    date = datetime.fromtimestamp(unix_time)
    past = datetime.today().date() - date.date()
    days = int(past.days)
    weeks = int(days / 7)
    months = int(days / 30)
    years = int(months / 12)

    if unix_time < 1:
        return _("never")
    elif days < 1:
        return _("today")
    elif days < 2:
        return _("yesterday")
    elif days < 7:
        return _("%s days ago") % str(days)
    elif weeks < 5:
        return ngettext('{weeks} week ago', '{weeks} weeks ago', weeks).format(weeks=weeks)
    elif months < 12:
        return ngettext('{months} month ago', '{months} months ago', months).format(months=months)
    else:
        return ngettext('{years} year ago', '{years} years ago', years).format(years=years)

def __get_media_type(path):
    """
    Get the mime type of a file.
    :param path: Path to the file
    :return: mime type as string
    """
    return magic.from_file(path, mime=True)

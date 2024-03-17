import threading
import time
from datetime import datetime
from gettext import ngettext


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
    if h > 0 and m > 0:
        result = ngettext('{hours} hour', '{hours} hours', h).format(hours=h) + \
                 " " + \
                 ngettext('{minutes} minute', '{minutes} minutes', m).format(minutes=m)
    elif h > 0:
        result = ngettext('{hours} hour', '{hours} hours', h).format(hours=h)
    elif m > 0:
        result = ngettext('{minutes} minute', '{minutes} minutes', m).format(minutes=m)
    elif s > 0:
        result = ngettext('{seconds} second', '{seconds} seconds', s).format(seconds=s)
    else:
        result = _("finished")

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

import time
import threading
import logging as log
import platform
import os
from gi.repository import GLib, Gio

def get_cache_dir():
    """
    Creates the cache dir if it doesn't exist
    :return: The path to the own cache dir
    """
    cache_dir = os.path.join(GLib.get_user_cache_dir(), "cozy")

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    return cache_dir

def shorten_string(string, length):
    """
    Shortens a string when it is longer than length and adds ... at the end.
    :param string: Text to be shortened
    :param length: Max. length of string
    :return : string or shortened string
    """
    return (string[:length] + '...') if len(string) > length else string

def is_elementary():
        """
        Currently we are only checking for elementaryOS
        """
        log.debug(platform.dist())
        if '"elementary"' in platform.dist():
            return True
        else:
            return False


settings = Gio.Settings.new("com.github.geigi.cozy")
def get_glib_settings():
    global settings
    return settings


# From https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds-in-python
class RepeatedTimer(object):
    """
    A timer that gets called after a specified amount of time.
    """
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.next_call = time.time()
        self.start()

    def _run(self):
        """
        Process the timer.
        """
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        """
        Start the timer.
        """
        if not self.is_running:
            self.next_call += self.interval
            self._timer = threading.Timer(
                self.next_call - time.time(), self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        """
        Stop the timer.
        """
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self.is_running = False


def seconds_to_str(seconds, include_seconds=True):
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
        else:
            result = "00:%02d" % (s)
    else:
        if (h > 0):
            result = "%d:%02d" % (h, m)
        elif (m > 0):
            result = "00:%02d" % (m)
        else:
            result = "00:00"

    return result

def remove_all_children(container):
        """
        Removes all widgets from a gtk container.
        """
        childs = container.get_children()
        for element in childs:
            container.remove(element)
            element.destroy()
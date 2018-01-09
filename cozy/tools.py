import time
import threading
import logging as log
import platform

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

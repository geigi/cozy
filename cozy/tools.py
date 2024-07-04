import threading
import time
from datetime import datetime
from gettext import ngettext


# https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target=None):
        super().__init__(target=target)
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

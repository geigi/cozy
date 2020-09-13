from typing import Callable

from cozy.report import reporter
import logging

log = logging.getLogger("observable")


class Observable:
    def __init__(self):
        self._observers = {}

    def bind_to(self, prop: str, callback: Callable):
        if prop in self._observers:
            self._observers[prop].append(callback)
        else:
            self._observers[prop] = [callback]

    def _notify(self, prop: str):
        try:
            for callback in self._observers[prop]:
                callback()
        except Exception as e:
            log.error(e)
            reporter.exception("observable", e)

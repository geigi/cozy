from typing import Callable


class Observable:
    def __init__(self):
        self._observers = {}

    def bind_to(self, prop: str, callback: Callable):
        if prop in self._observers:
            self._observers[prop].append(callback)
        else:
            self._observers[prop] = [callback]

    def _notify(self, prop: str, value):
        try:
            for callback in self._observers[prop]:
                callback(value)
        except:
            pass

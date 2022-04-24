from typing import Callable

from gi.repository import Gdk, GLib

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

    def remove_bind(self, prop: str, callback: Callable):
        if not prop:
            log.error("Cannot remove bind for empty prop.")
            reporter.error("observable", "Cannot remove bind for empty prop.")
            return

        if not callback:
            log.error("Cannot remove bind for empty callback.")
            reporter.error("observable", "Cannot remove bind for empty callback.")
            return

        if prop in self._observers:
            if callback in self._observers[prop]:
                self._observers[prop].remove(callback)
            else:
                log.info("Callback not found in prop's {} observers. Skipping remove bind...".format(prop))
        else:
            log.info("Prop not found in observers. Skipping remove bind...")

    def _notify(self, prop: str):
        try:
            if prop in self._observers:
                for callback in self._observers[prop]:
                    callback()
        except Exception as e:
            log.error(e)
            reporter.exception("observable", e)

    def _notify_main_thread(self, prop: str):
        GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, self._notify, (prop))

    def _destroy_observers(self):
        self._observers = {}

from typing import List, Callable

import gi
from gi.repository import GLib


class EventSender:
    _listeners: list[Callable]

    def __init__(self):
        self._listeners = []

    def emit_event(self, event, message=None):
        if isinstance(event, tuple) and message is None:
            event, message = event

        for function in self._listeners:
            function(event, message)

    def emit_event_main_thread(self, event: str, message=None):
        GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, self.emit_event, (event, message))

    def add_listener(self, function: Callable[[str, object], None]):
        self._listeners.append(function)

    def destroy_listeners(self):
        self._listeners = []

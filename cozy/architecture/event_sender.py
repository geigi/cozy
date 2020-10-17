from typing import List, Callable

from gi.repository import Gdk, GLib


class EventSender:
    _listeners: List[Callable]

    def __init__(self):
        self._listeners = []

    def emit_event(self, event, message=None):
        if type(event) is tuple and not message:
            message = event[1]
            event = event[0]

        for function in self._listeners:
            function(event, message)

    def emit_event_main_thread(self, event: str, message=None):
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, self.emit_event, (event, message))

    def add_listener(self, function: Callable[[str, object], None]):
        self._listeners.append(function)

    def destroy_listeners(self):
        self._listeners = []

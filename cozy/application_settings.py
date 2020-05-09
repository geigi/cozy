from gi.repository import Gio

from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton


class ApplicationSettings(EventSender, metaclass=Singleton):
    def __init__(self):
        self._settings: Gio.Settings = Gio.Settings("com.github.geigi.cozy")

        self._connect()

    def _connect(self):
        self._settings.connect("changed", self._key_changed)

    def _key_changed(self, settings: Gio.Settings, key: str):
        self.emit_event(key)

    @property
    def hide_offline(self):
        return self._settings.get_boolean("hide-offline")

from gi.repository import Gio

from cozy.architecture.singleton import Singleton


class ApplicationSettings(metaclass=Singleton):
    def __init__(self):
        self._settings: Gio.Settings = Gio.Settings("com.github.geigi.cozy")

    @property
    def hide_offline(self):
        return self._settings.get_boolean("hide-offline")

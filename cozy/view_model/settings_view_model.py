from cozy.application_settings import ApplicationSettings
from cozy.architecture.observable import Observable
from cozy.ext import inject
from cozy.media.importer import Importer
from cozy.model.settings import Settings
from gi.repository import Gtk


class SettingsViewModel(Observable, object):
    _importer: Importer = inject.attr(Importer)
    _model: Settings = inject.attr(Settings)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self):
        super().__init__()

        self._gtk_settings = Gtk.Settings.get_default()

        self._app_settings.add_listener(self._on_app_setting_changed)

        if self._model.first_start:
            self._importer.scan()

    def _set_dark_mode(self):
        prefer_dark_mode = self._app_settings.dark_mode
        self._gtk_settings.set_property("gtk-application-prefer-dark-theme", prefer_dark_mode)

    def _on_app_setting_changed(self, event: str, data):
        if event == "dark-mode":
            self._set_dark_mode()

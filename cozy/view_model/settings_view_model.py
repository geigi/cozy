import logging

from gi.repository import Adw

from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.ext import inject
from cozy.media.importer import Importer
from cozy.model.settings import Settings

log = logging.getLogger("settings_view_model")


class SettingsViewModel(Observable, EventSender):
    _importer: Importer = inject.attr(Importer)
    _model: Settings = inject.attr(Settings)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._lock_ui: bool = False

        self.style_manager = Adw.StyleManager.get_default()
        self._set_dark_mode()

        self._app_settings.add_listener(self._on_app_setting_changed)

        if self._model.first_start:
            self._importer.scan()

    @property
    def lock_ui(self) -> bool:
        return self._lock_ui

    @lock_ui.setter
    def lock_ui(self, new_value: bool):
        self._lock_ui = new_value
        self._notify("lock_ui")

    def _set_dark_mode(self):
        if self._app_settings.dark_mode:
            self.style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            self.style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)

    def _on_app_setting_changed(self, event: str, data):
        if event == "dark-mode":
            self._set_dark_mode()

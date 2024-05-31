import logging

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

        if self._model.first_start:
            self._importer.scan()

    @property
    def lock_ui(self) -> bool:
        return self._lock_ui

    @lock_ui.setter
    def lock_ui(self, new_value: bool):
        self._lock_ui = new_value
        self._notify("lock_ui")

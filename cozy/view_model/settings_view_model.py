from cozy.architecture.observable import Observable
from cozy.ext import inject
from cozy.media.importer import Importer
from cozy.model.settings import Settings


class SettingsViewModel(Observable, object):
    _importer: Importer = inject.attr(Importer)
    _model: Settings = inject.attr(Settings)

    def __init__(self):
        super().__init__()

        self._swap_author_reader: bool = None

        if self._model.first_start:
            self._importer.scan()

    @property
    def swap_author_reader(self):
        return self._swap_author_reader

    @swap_author_reader.setter
    def swap_author_reader(self, value):
        self._swap_author_reader = value
        for callback in self._observers["swap_author_reader"]:
            callback(value)

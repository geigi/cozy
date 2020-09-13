from cozy.architecture.observable import Observable


class SettingsViewModel(Observable, object):

    def __init__(self):
        super().__init__()

        self._swap_author_reader: bool = None

    @property
    def swap_author_reader(self):
        return self._swap_author_reader

    @swap_author_reader.setter
    def swap_author_reader(self, value):
        self._swap_author_reader = value
        for callback in self._observers["swap_author_reader"]:
            callback(value)

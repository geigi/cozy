from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable


class HeaderbarViewModel(Observable, EventSender):

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._lock_ui: bool = False

    @property
    def lock_ui(self) -> bool:
        return self._lock_ui

    @lock_ui.setter
    def lock_ui(self, new_value: bool):
        self._lock_ui = new_value
        self._notify("lock_ui")

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.view import View


class AppViewModel(Observable, EventSender):
    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._view = View.EMPTY_STATE

    @property
    def view(self) -> View:
        return self._view

    @view.setter
    def view(self, new_value: View):
        self._view = new_value
        self._notify("view")
        self.emit_event_main_thread("view", self._view)

    def navigate_back(self):
        if self.view == View.BOOK_DETAIL:
            self.view = View.LIBRARY_BOOKS
        elif self.view == View.LIBRARY_BOOKS:
            self.view = View.LIBRARY_FILTER

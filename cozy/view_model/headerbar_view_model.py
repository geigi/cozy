from enum import Enum, auto

import inject

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.offline_cache import OfflineCache
from cozy.media.files import Files
from cozy.media.importer import Importer, ScanStatus
from cozy.model.library import Library
from cozy.view import View


class HeaderBarState(Enum):
    PLAYING = auto()
    WORKING = auto()


class HeaderbarViewModel(Observable, EventSender):
    _importer: Importer = inject.attr(Importer)
    _files: Files = inject.attr(Files)
    _library: Library = inject.attr(Library)
    _offline_cache: OfflineCache = inject.attr(OfflineCache)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._state: HeaderBarState = HeaderBarState.PLAYING
        self._work_progress: float = 0.0
        self._work_message: str = ""
        self._view: View = View.EMPTY_STATE

        self._importer.add_listener(self._on_importer_event)
        self._files.add_listener(self._on_files_event)
        self._library.add_listener(self._on_library_event)
        self._offline_cache.add_listener(self._on_offline_cache_event)

    @property
    def lock_ui(self) -> bool:
        return self._view in {View.NO_MEDIA, View.EMPTY_STATE, View.PREPARING_LIBRARY}

    @property
    def state(self) -> HeaderBarState:
        return self._state

    @property
    def work_progress(self) -> float:
        return min(self._work_progress, 1.0)

    @property
    def work_message(self) -> str:
        return self._work_message

    def set_view(self, value: View):
        self._view = value
        self._notify("lock_ui")

    def _start_working(self, message: str):
        self._work_progress = 0.0
        self._state = HeaderBarState.WORKING
        self._work_message = message
        self._notify("work_message")
        self._notify("work_progress")
        self._notify("state")
        self.emit_event_main_thread("working", True)

    def _stop_working(self):
        self._state = HeaderBarState.PLAYING
        self._notify("state")
        self.emit_event_main_thread("working", False)

    def _on_importer_event(self, event: str, message):
        if event == "scan-progress" and isinstance(message, float):
            self._work_progress = message
            self._notify("work_progress")
        elif event == "scan" and message == ScanStatus.STARTED:
            self._start_working(_("Refreshing audio book collection"))
        elif event == "scan" and message == ScanStatus.SUCCESS:
            self._stop_working()

    def _on_files_event(self, event: str, message):
        if event == "copy-progress" and isinstance(message, float):
            self._work_progress = message
            self._notify("work_progress")
        elif event == "start-copy":
            self._start_working(_("Copying new files…"))

    def _on_library_event(self, event: str, message):
        if event == "rebase-progress" and isinstance(message, float):
            self._work_progress = message
            self._notify("work_progress")
        elif event == "rebase-started":
            self._start_working(_("Changing audio book location…"))
        elif event == "rebase-finished":
            self._stop_working()

    def _on_offline_cache_event(self, event: str, message):
        if event == "progress" and isinstance(message, float):
            self._work_progress = message
            self._notify("work_progress")
        elif event == "start":
            self._start_working(_("Copying new files…"))
        elif event == "message":
            self._work_message = message
            self._notify("work_message")
        elif event == "finished":
            self._stop_working()


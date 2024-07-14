import inject

from cozy import tools
from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.control.offline_cache import OfflineCache
from cozy.media.player import Player
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library
from cozy.model.settings import Settings
from cozy.open_view import OpenView


class BookDetailViewModel(Observable, EventSender):
    _player: Player = inject.attr(Player)
    _fs_monitor: FilesystemMonitor = inject.attr("FilesystemMonitor")
    _offline_cache: OfflineCache = inject.attr(OfflineCache)
    _settings: Settings = inject.attr(Settings)
    _library = Library = inject.attr(Library)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._play = False
        self._current_chapter = None
        self._book: Book | None = None
        self._lock_ui: bool = False

        self._player.add_listener(self._on_player_event)
        self._fs_monitor.add_listener(self._on_fs_monitor_event)
        self._offline_cache.add_listener(self._on_offline_cache_event)
        self._app_settings.add_listener(self._on_app_setting_changed)

    @property
    def playing(self) -> bool:
        if not self._player.loaded_book or self._player.loaded_book != self._book:
            return False

        return self._player.playing

    @property
    def current_chapter(self) -> Chapter | None:
        if not self.book:
            return None

        return self.book.current_chapter

    @property
    def book(self) -> Book | None:
        return self._book

    @book.setter
    def book(self, value: Book):
        if self._book == value:
            return

        if self._book:
            self._book.remove_bind("current_chapter", self._on_book_current_chapter_changed)
            self._book.remove_bind("last_played", self._on_book_last_played_changed)
            self._book.remove_bind("duration", self._on_book_duration_changed)
            self._book.remove_bind("progress", self._on_book_progress_changed)
            self._book.remove_bind("playback_speed", self._on_playback_speed_changed)

        self._book = value
        self._current_chapter = None
        self._book.bind_to("current_chapter", self._on_book_current_chapter_changed)
        self._book.bind_to("last_played", self._on_book_last_played_changed)
        self._book.bind_to("duration", self._on_book_duration_changed)
        self._book.bind_to("progress", self._on_book_progress_changed)
        self._book.bind_to("playback_speed", self._on_playback_speed_changed)
        self._notify("book")

    @property
    def last_played_text(self) -> str | None:
        if not self._book:
            return None

        return tools.past_date_to_human_readable(self._book.last_played)

    @property
    def total_text(self) -> str | None:
        if not self._book:
            return None

        return tools.seconds_to_human_readable(self._book.duration / self._book.playback_speed)

    @property
    def remaining_text(self) -> str | None:
        if not self._book:
            return None

        remaining = self._book.duration - self._book.progress
        return tools.seconds_to_human_readable(remaining / self._book.playback_speed)

    @property
    def progress_percent(self) -> float | None:
        if not self._book:
            return None
        elif self._book.duration < 1:
            return 1.0

        return self._book.progress / self._book.duration

    @property
    def disk_count(self) -> int:
        if not self._book:
            return 0

        return len({chapter.disk for chapter in self._book.chapters})

    @property
    def is_book_available(self) -> bool:
        if self._book.offline and self._book.downloaded:
            return True

        return self._fs_monitor.get_book_online(self._book)

    @property
    def is_book_external(self) -> bool:
        first_chapter_path = self._book.chapters[0].file
        for storage in self._settings.external_storage_locations:
            if storage.path in first_chapter_path:
                return True
        return False

    @property
    def lock_ui(self) -> bool:
        return self._lock_ui

    @lock_ui.setter
    def lock_ui(self, new_value: bool):
        self._lock_ui = new_value
        self._notify("lock_ui")

    def download_book(self, download: bool):
        self._book.offline = download

        if download:
            self._offline_cache.add(self._book)
        else:
            self._offline_cache.remove(self._book)

    def open_library(self):
        self.emit_event(OpenView.LIBRARY)

    def play_book(self):
        self._player.play_pause_book(self.book)

    def play_chapter(self, chapter: Chapter):
        if self._book.current_chapter != chapter:
            chapter.position = chapter.start_position
        self._player.play_pause_chapter(self._book, chapter)

    def open_book_detail_view(self):
        self._notify("open")

    def _on_player_event(self, event, message):
        if not self.book:
            return

        if event in {"play", "pause"}:
            self._notify("playing")
        elif event in {"position", "book-finished"}:
            self._notify("progress_percent")
            self._notify("remaining_text")

    def _on_fs_monitor_event(self, event, _):
        if not self._book:
            return

        if event in {"storage-online", "storage-offline"}:
            self._notify("is_book_available")

    def _on_book_current_chapter_changed(self):
        self._notify("current_chapter")

    def _on_book_last_played_changed(self):
        self._notify("last_played_text")

    def _on_book_progress_changed(self):
        self._notify("remaining_text")
        self._notify("progress_percent")

    def _on_book_duration_changed(self):
        self._notify("progress_percent")
        self._notify("remaining_text")
        self._notify("total_text")

    def _on_playback_speed_changed(self):
        self._notify("progress_percent")
        self._notify("remaining_text")
        self._notify("total_text")

    def _on_offline_cache_event(self, event, message):
        if not (message and self._book) or self._book.id != message.id:
            return

        if event in {"book-offline-removed", "book-offline"}:
            self._notify("downloaded")

    def _on_app_setting_changed(self, event, _):
        if event == "swap-author-reader":
            self._notify("book")

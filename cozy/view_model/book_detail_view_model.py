from typing import Optional

from cozy import tools
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control.filesystem_monitor import FilesystemMonitor
from cozy.control.offline_cache import OfflineCache
from cozy.ext import inject
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

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._play = False
        self._current_chapter = None
        self._book = None

        self._player.add_listener(self._on_player_event)
        self._fs_monitor.add_listener(self._on_fs_monitor_event)

    @property
    def playing(self) -> bool:
        if not self._player.loaded_book or self._player.loaded_book != self._book:
            return False

        return self._player.playing

    @property
    def current_chapter(self) -> Optional[Chapter]:
        return self.current_chapter

    @current_chapter.setter
    def current_chapter(self, value: Chapter):
        self._current_chapter = value
        self._notify("current_chapter")

    @property
    def book(self) -> Optional[Book]:
        return self._book

    @book.setter
    def book(self, value: Book):
        self._book = value
        self._current_chapter = None
        self._notify("book")

    @property
    def last_played_text(self) -> Optional[str]:
        if not self._book:
            return None

        return tools.past_date_to_human_readable(self._book.last_played)

    @property
    def total_text(self) -> Optional[str]:
        if not self._book:
            return None

        return tools.seconds_to_human_readable(self._book.duration)

    @property
    def remaining_text(self) -> Optional[str]:
        if not self._book:
            return None

        remaining = self._book.duration - self._book.progress
        return tools.seconds_to_human_readable(remaining)

    @property
    def progress_percent(self) -> Optional[float]:
        if not self._book:
            return None

        if self._book.duration < 1:
            return 1.0

        return self._book.progress / self._book.duration

    @property
    def disk_count(self) -> int:
        if not self._book:
            return 0

        return len({chapter.disk
                    for chapter
                    in self._book.chapters})

    @property
    def is_book_available(self) -> bool:
        return self._fs_monitor.get_book_online(self._book)

    @property
    def is_book_external(self) -> bool:
        first_chapter_path = self._book.chapters[0].file
        return any(first_chapter_path
                   in storage.path
                   for storage
                   in self._settings.external_storage_locations)

    def download_book(self, download: bool):
        self._book.offline = download

        if download:
            self._offline_cache.add(self._book.db_object)
        else:
            self._offline_cache.remove(self._book.db_object)

    def open_library(self):
        self.emit_event(OpenView.LIBRARY)

    def play_book(self):
        self._player.play_pause_book(self.book)

    def play_chapter(self, chapter: Chapter):
        self.current_chapter = chapter
        self._player.play_pause_chapter(self._book, self._current_chapter)

    def _on_player_event(self, event, message):
        if event == "play" or event == "pause":
            self._notify("playing")

    def _on_fs_monitor_event(self, event, _):
        if event == "storage-online":
            self._notify("is_book_available")
        elif event == "storage-offline":
            self._notify("is_book_available")

    def __on_offline_cache_event(self, event, message):
        """
        """
        try:
            if message.id != self._book.db_object.id:
                return
        except Exception as e:
            return

        if event == "book-offline":
            self._notify("downloaded")

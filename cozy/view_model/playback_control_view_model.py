from typing import Optional

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.ext import inject
from cozy.media.player import Player
from cozy.model.book import Book


class PlaybackControlViewModel(Observable, EventSender):
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._book: Book = None
        self._lock_ui: bool = True

        self._player.add_listener(self._on_player_event)

    @property
    def book(self) -> Optional[Book]:
        return self._book

    @property
    def playing(self) -> bool:
        if not self._player.loaded_book:
            return False

        return self._player.playing

    @property
    def position(self) -> Optional[float]:
        if not self._player.loaded_book:
            return None

        return self._player.position / 1000000000

    @property
    def length(self) -> Optional[float]:
        if not self._player.loaded_book:
            return None

        return self._player.loaded_book.current_chapter.length

    @property
    def lock_ui(self) -> bool:
        return self._lock_ui

    @lock_ui.setter
    def lock_ui(self, new_value: bool):
        self._lock_ui = new_value
        self._notify("lock_ui")

    def _on_player_event(self, event, message):
        if event == "play" or event == "pause":
            if self.book:
                self._notify("playing")
        elif event == "position":
            if self.book:
                self._notify("position")
                self._notify("progress_percent")
                self._notify("remaining_text")
        elif event == "track-changed":
            if message:
                self._book = message
                self.lock_ui = False
                self._notify("book")
                self._notify("position")
                self._notify("length")
            else:
                self.lock_ui = True

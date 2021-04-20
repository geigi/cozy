from typing import Optional

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.ext import inject
from cozy.media.player import Player
from cozy.model.book import Book
from cozy.open_view import OpenView


class PlaybackControlViewModel(Observable, EventSender):
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._book: Optional[Book] = None

        self._player.add_listener(self._on_player_event)

        if self._player.loaded_book:
            self.book = self._player.loaded_book

    @property
    def book(self) -> Optional[Book]:
        return self._book

    @book.setter
    def book(self, value: Optional[Book]):
        if self._book:
            self._book.remove_bind("playback_speed", self._on_playback_speed_changed)

        self._book = value
        if value:
            self._book.bind_to("playback_speed", self._on_playback_speed_changed)

        self._notify("lock_ui")

    @property
    def playing(self) -> bool:
        if not self._player.loaded_book:
            return False

        return self._player.playing

    @property
    def position(self) -> Optional[float]:
        if not self._book:
            return None

        return self._book.current_chapter.position / 1000000000 / self._book.playback_speed

    @position.setter
    def position(self, new_value: int):
        self._player.position = new_value

    @property
    def length(self) -> Optional[float]:
        if not self._player.loaded_book or not self._book:
            return None

        return self._player.loaded_book.current_chapter.length / self._book.playback_speed

    @property
    def lock_ui(self) -> bool:
        return not self._book

    @property
    def volume(self) -> float:
        return self._player.volume

    @volume.setter
    def volume(self, new_value: float):
        self._player.volume = new_value

    def play_pause(self):
        self._player.play_pause()

    def rewind(self):
        self._player.rewind()

    def forward(self):
        self._player.forward()

    def open_book_detail(self):
        if self.book:
            self.emit_event(OpenView.BOOK, self.book)

    def _on_player_event(self, event, message):
        if event == "play" or event == "pause":
            if self.book:
                self._notify("playing")
        elif event == "position":
            if self.book:
                self._notify("position")
                self._notify("progress_percent")
                self._notify("remaining_text")
        elif event == "chapter-changed":
            if message:
                self.book = message
                self._notify("book")
                self._notify("position")
                self._notify("length")
                self._notify("volume")
        elif event == "stop":
            self.book = None
            self._notify("book")
            self._notify("position")
            self._notify("length")

    def _on_playback_speed_changed(self):
        self._notify("position")
        self._notify("length")

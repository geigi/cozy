import inject
from gi.repository import Gst

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.media.player import Player
from cozy.model.book import Book
from cozy.open_view import OpenView


class PlaybackControlViewModel(Observable, EventSender):
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._book: Book | None = None

        self._player.add_listener(self._on_player_event)

        if self._player.loaded_book:
            self.book = self._player.loaded_book

    @property
    def book(self) -> Book | None:
        return self._book

    @book.setter
    def book(self, value: Book | None):
        self._book = value
        self._notify("lock_ui")

    @property
    def playing(self) -> bool:
        if not self._player.loaded_book:
            return False

        return self._player.playing

    @property
    def position(self) -> float | None:
        if not self._book:
            return None

        position = self._book.current_chapter.position - self._book.current_chapter.start_position
        return position / Gst.SECOND / self._book.playback_speed

    @position.setter
    def position(self, new_value: int):
        if not self._book:
            return

        self._player.position = new_value * Gst.SECOND * self._book.playback_speed

    @property
    def length(self) -> float | None:
        if not self._player.loaded_book or not self._book:
            return None

        return self._player.loaded_book.current_chapter.length / self._book.playback_speed

    @property
    def relative_position(self) -> float | None:
        if not self._player.loaded_book or not self._book:
            return None

        position = self._book.current_chapter.position - self._book.current_chapter.start_position
        length = self._player.loaded_book.current_chapter.length
        return position / length * 100

    @relative_position.setter
    def relative_position(self, new_value: float) -> None:
        if not self._book:
            return

        length = self._player.loaded_book.current_chapter.length
        self._player.position = int(length * new_value / 100)

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
        self._player._emit_tick()

    def forward(self):
        self._player.forward()
        self._player._emit_tick()

    def open_book_detail(self):
        if self.book:
            self.emit_event(OpenView.BOOK, self.book)

    def _on_player_event(self, event, message):
        if event in {"play", "pause"}:
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

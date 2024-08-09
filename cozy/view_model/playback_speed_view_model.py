import inject

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.db.book import Book
from cozy.media.player import Player


class PlaybackSpeedViewModel(Observable, EventSender):
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._book: Book = self._player.loaded_book

        self._player.add_listener(self._on_player_event)

    @property
    def playback_speed(self) -> float:
        if self._book:
            return self._book.playback_speed

        return 1.0

    @playback_speed.setter
    def playback_speed(self, new_value: float):
        if self._book:
            self._book.playback_speed = new_value
            self._player.playback_speed = new_value

    def _on_player_event(self, event: str, message):
        if event == "chapter-changed" and message:
            self._book = message
            self._notify("playback_speed")

    def speed_up(self):
        self.playback_speed = min(self.playback_speed + .1, 3.5)
        self._notify("playback_speed")

    def speed_down(self):
        self.playback_speed = max(self.playback_speed - .1, 0.5)
        self._notify("playback_speed")

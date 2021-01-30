from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.control import player
from cozy.db.book import Book
from cozy.ext import inject
from cozy.media.player import Player


class PlaybackSpeedViewModel(Observable, EventSender):
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._book: Book = None

        self._player.add_listener(self._on_player_event)

    @property
    def playback_speed(self) -> float:
        if self._book:
            return self._book.playback_speed
        else:
            return 1.0

    @playback_speed.setter
    def playback_speed(self, new_value: float):
        if self._book:
            self._book.playback_speed = new_value
            player.set_playback_speed(new_value)

    def _on_player_event(self, event: str, message):
        if event == "track-changed" and message:
            self._book = message
            self._notify("playback_speed")

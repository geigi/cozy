from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton
from cozy.control import player
from cozy.model.book import Book


class Player(EventSender):
    def __init__(self):
        super().__init__()
        self._gst_player: player = player.get_playbin()
        player.add_player_listener(self._pass_legacy_player_events)

    def play_pause(self, book: Book):
        pass

    def _pass_legacy_player_events(self, event, message):
        if event == "play" and message:
            message = message.id
        self.emit_event(event, message)

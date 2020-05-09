from cozy.architecture.singleton import Singleton
from cozy.control import player
from cozy.model.book import Book


class Player(metaclass=Singleton):
    def __init__(self):
        self._gst_player: player = player.get_playbin()

    def play_pause(self, book: Book):
        pass

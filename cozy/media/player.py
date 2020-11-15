from cozy.architecture.event_sender import EventSender
from cozy.control import player
from cozy.model.book import Book
from cozy.model.chapter import Chapter


class Player(EventSender):
    def __init__(self):
        super().__init__()
        self._gst_player: player = player.get_playbin()
        player.add_player_listener(self._pass_legacy_player_events)

    def play_pause_book(self, book: Book):
        current_track = player.get_current_track()

        if current_track and book.current_chapter.file == current_track.file:
            player.play_pause(None)
        else:
            player.load_file(book.current_chapter._db_object)
            player.play_pause(None, True)

    def play_pause_chapter(self, book: Book, chapter: Chapter):
        current_track = player.get_current_track()
        
        if current_track and current_track.file == chapter.file:
            player.play_pause(None)
        else:
            player.load_file(chapter._db_object)
            player.play_pause(None, True)
            book.position = chapter.id

    def _pass_legacy_player_events(self, event, message):
        if event == "play" and message:
            message = message.id
        self.emit_event(event, message)

from cozy.architecture.event_sender import EventSender
from cozy.control import player
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library


class Player(EventSender):
    _library: Library = inject.attr(Library)

    def __init__(self):
        super().__init__()
        self._gst_player: player = player.get_playbin()
        player.add_player_listener(self._pass_legacy_player_events)

    @property
    def loaded_book(self) -> Book:
        current_track = player.get_current_track()
        if not current_track:
            return None

        track_id = current_track.id
        book = None

        for b in self._library.books:
            if any(chapter.id == track_id for chapter in b.chapters):
                book = b
                break

        return book

    @property
    def playing(self) -> bool:
        return player.is_playing()

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
        if (event == "play" or event == "pause") and message:
            message = message.id

        self.emit_event(event, message)

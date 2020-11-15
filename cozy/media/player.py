import logging
import time
from typing import Optional

from cozy.architecture.event_sender import EventSender
from cozy.control import player
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library
from cozy.report import reporter

log = logging.getLogger("mediaplayer")


class Player(EventSender):
    _library: Library = inject.attr(Library)

    def __init__(self):
        super().__init__()
        self._gst_player: player = player.get_playbin()
        player.add_player_listener(self._pass_legacy_player_events)

    @property
    def loaded_book(self) -> Optional[Book]:
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
    def loaded_chapter(self) -> Optional[Chapter]:
        current_track = player.get_current_track()
        if not current_track:
            return None

        chapter = None

        for c in self._library.chapters:
            if c.id == current_track.id:
                chapter = c

        return chapter

    @property
    def playing(self) -> bool:
        return player.is_playing()

    @property
    def position(self) -> int:
        return player.get_current_duration()

    def play_pause_book(self, book: Book):
        if not book:
            log.error("Cannot play book which is None.")
            reporter.error("player", "Cannot play book which is None.")
            return

        current_track = player.get_current_track()

        book.last_played = int(time.time())
        if current_track and book.current_chapter.file == current_track.file:
            player.play_pause(None)
        else:
            player.load_file(book.current_chapter._db_object)
            player.play_pause(None, True)

    def play_pause_chapter(self, book: Book, chapter: Chapter):
        if not book or not chapter:
            log.error("Cannot play chapter which is None.")
            reporter.error("player", "Cannot play chapter which is None.")
            return

        current_track = player.get_current_track()

        book.last_played = int(time.time())
        if current_track and current_track.file == chapter.file:
            player.play_pause(None)
        else:
            player.load_file(chapter._db_object)
            player.play_pause(None, True)
            book.position = chapter.id

    def _pass_legacy_player_events(self, event, message):
        if (event == "play" or event == "pause") and message:
            message = message.id
        # this is evil and will be removed when the old player is replaced
        if event == "track-changed":
            book = self.loaded_book
            if book and message:
                book.position = message.id
        if event == "book-finished":
            book = self.loaded_book
            if book:
                book.position = -1

        self.emit_event(event, message)

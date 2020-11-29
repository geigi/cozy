import logging
import time
from typing import Optional

from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.control import player
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library
from cozy.report import reporter
from cozy.tools import IntervalTimer

log = logging.getLogger("mediaplayer")


class Player(EventSender):
    _library: Library = inject.attr(Library)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self):
        super().__init__()
        self._first_play = True
        self._gst_player: player = player.get_playbin()
        player.add_player_listener(self._pass_legacy_player_events)

        self.play_status_updater: IntervalTimer = IntervalTimer(1, self._emit_tick)

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

        self._play_chapter(book, book.current_chapter)

    def play_pause_chapter(self, book: Book, chapter: Chapter):
        if not book or not chapter:
            log.error("Cannot play chapter which is None.")
            reporter.error("player", "Cannot play chapter which is None.")
            return

        self._play_chapter(book, chapter)
        book.position = chapter.id

    def _play_chapter(self, book: Book, chapter: Chapter):
        current_track = player.get_current_track()

        book.last_played = int(time.time())
        if current_track and current_track.file == chapter.file:
            player.play_pause(None)
        else:
            player.load_file(chapter._db_object)
            player.play_pause(None, True)

    def rewind(self):
        if self.loaded_book:
            player.rewind(30 / self.loaded_book.playback_speed)

    def _rewind_feature(self):
        if self._first_play and self._app_settings.replay:
            self._first_play = False
            player.rewind(30 / self.loaded_book.playback_speed)

    def _pass_legacy_player_events(self, event, message):
        if event == "play":
            self._start_tick_thread()
        elif event == "stop" or event == "pause" or event == "closing":
            self._stop_tick_thread()
        if (event == "play" or event == "pause") and message:
            message = message.id
            # TODO: This needs to be done when the last chapter is first loaded after startup
            if self._first_play:
                self._rewind_feature()
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

    def _start_tick_thread(self):
        if self.play_status_updater:
            self.play_status_updater.stop()

        self.play_status_updater = IntervalTimer(1, self._emit_tick)
        self.play_status_updater.start()

    def _stop_tick_thread(self):
        if self.play_status_updater:
            self.play_status_updater.stop()
            self.play_status_updater = None

    def _emit_tick(self):
        if self.loaded_chapter:
            self.loaded_chapter.position = self.position

        self.emit_event_main_thread("position", self.position)

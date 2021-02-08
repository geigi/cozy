import logging
import time
from threading import Thread
from typing import Optional

from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.ext import inject
from cozy.media.gst_player import GstPlayer, GstPlayerState
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library
from cozy.report import reporter
from cozy.tools import IntervalTimer

log = logging.getLogger("mediaplayer")

NS_TO_SEC = 10 ** 9
REWIND_SECONDS = 30


class Player(EventSender):
    _library: Library = inject.attr(Library)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    _gst_player: GstPlayer = inject.attr(GstPlayer)

    def __init__(self):
        super().__init__()

        self._book: Optional[Book] = None
        self._play_next_chapter: bool = True

        self._gst_player.add_listener(self._on_gst_player_event)

        self.play_status_updater: IntervalTimer = IntervalTimer(1, self._emit_tick)
        self._fadeout_thread: Optional[Thread] = None

        self._gst_player.init()

        self._load_last_book()

    def _load_last_book(self):
        last_book = self._library.last_played_book

        if last_book:
            self._load_book(last_book)
            self._rewind_feature()

    @property
    def loaded_book(self) -> Optional[Book]:
        return self._book

    @property
    def loaded_chapter(self) -> Optional[Chapter]:
        return self._book.current_chapter

    @property
    def playing(self) -> bool:
        return self._gst_player.state == GstPlayerState.PLAYING

    @property
    def position(self) -> int:
        return self._gst_player.position

    @position.setter
    def position(self, new_value: int):
        self._gst_player.position = new_value * NS_TO_SEC

    @property
    def volume(self) -> float:
        return self._gst_player.volume

    @volume.setter
    def volume(self, new_value: float):
        self._gst_player.volume = new_value
        self._app_settings.volume = new_value

    @property
    def play_next_chapter(self) -> bool:
        return self._play_next_chapter

    @play_next_chapter.setter
    def play_next_chapter(self, value: bool):
        self._play_next_chapter = value

    @property
    def playback_speed(self) -> float:
        return self._gst_player.playback_speed

    @playback_speed.setter
    def playback_speed(self, value: float):
        self._gst_player.playback_speed = value

    def play_pause(self):
        if self._gst_player.state == GstPlayerState.PAUSED:
            self._gst_player.play()
        elif self._gst_player.state == GstPlayerState.PLAYING:
            self._gst_player.pause()
        else:
            log.error("Trying to play/pause although player is in STOP state.")
            reporter.error("player", "Trying to play/pause although player is in STOP state.")

    def pause(self, fadeout: bool = False):
        if fadeout and not self._fadeout_thread:
            log.info("Starting fadeout playback")
            self._fadeout_thread = Thread(target=self._fadeout_playback, name="PlayerFadeoutThread")
            self._fadeout_thread.start()
            return

        if self._gst_player.state == GstPlayerState.PLAYING:
            self._gst_player.pause()

    def play_pause_book(self, book: Book):
        if not book:
            log.error("Cannot play book which is None.")
            reporter.error("player", "Cannot play book which is None.")
            return

        if self._book == book:
            self.play_pause()
        else:
            self._load_book(book)
            self._gst_player.play()

    def play_pause_chapter(self, book: Book, chapter: Chapter):
        if not book or not chapter:
            log.error("Cannot play chapter which is None.")
            reporter.error("player", "Cannot play chapter which is None.")
            return

        if self._book and self._book.current_chapter == chapter:
            self.play_pause()

        if not self._book:
            self._book = book

        self._load_chapter(chapter)
        self._gst_player.play()

        book.position = chapter.id

    def rewind(self):
        state = self._gst_player.state
        if state != GstPlayerState.STOPPED:
            self._rewind_in_book()
        if state == GstPlayerState.PLAYING:
            self._gst_player.play()

    def destroy(self):
        self._gst_player.dispose()

        self._stop_tick_thread()

        if self._fadeout_thread:
            self._fadeout_thread.stop()

    def _load_book(self, book: Book):
        if self._book == book:
            log.info("Not loading new book because it's unchanged.")
            return

        self._book = book
        self._book.last_played = int(time.time())
        self._load_chapter(self._book.current_chapter)
        self.emit_event("chapter-changed", self._book)

    def _load_chapter(self, chapter: Chapter):
        if not self._book:
            log.error("There is no book loaded but there should be.")
            reporter.error("player", "There is no book loaded but there should be.")

        if self._gst_player.loaded_file_path == self._book.current_chapter.file:
            log.info("Not loading a new file because the new chapter is within the old file.")
        else:
            log.info("Loading new file for chapter.")
            self._gst_player.load_file(chapter.file)

        self._gst_player.position = chapter.position

        if self._book.position != chapter.id:
            self._book.position = chapter.id
            self.emit_event("chapter-changed", self._book)

    def _rewind_in_book(self):
        current_position = self._gst_player.position
        chapter_number = self._book.chapters.index(self._book.current_chapter)

        if current_position / NS_TO_SEC - REWIND_SECONDS > 0:
            self._gst_player.position = current_position - NS_TO_SEC * REWIND_SECONDS
        elif chapter_number > 0:
            previous_chapter = self._book.chapters[chapter_number - 1]
            self._load_chapter(previous_chapter)
            self._gst_player.position = previous_chapter.end_position + (current_position - NS_TO_SEC * REWIND_SECONDS)
        else:
            self._gst_player.position = 0

    def _rewind_feature(self):
        pass
        if self._app_settings.replay:
            self._rewind_in_book()

    def _next_chapter(self):
        if not self._book:
            log.error("Cannot play next chapter because no book reference is stored.")
            reporter.error("player", "Cannot play next chapter because no book reference is stored.")

        index_current_chapter = self._book.chapters.index(self._book.current_chapter)

        if len(self._book.chapters) <= index_current_chapter + 1:
            log.info("Book finished, stopping playback.")
            self._finish_book()
            self._gst_player.stop()
        else:
            chapter = self._book.chapters[index_current_chapter + 1]
            chapter.position = chapter.start_position
            self.play_pause_chapter(self._book, chapter)

    def _on_gst_player_event(self, event: str, message):
        if event == "file-finished":
            self._next_chapter()
        elif event == "resource-not-found":
            self._book = None
        elif event == "state" and message == GstPlayerState.PLAYING:
            self._book.last_played = int(time.time())
            self._start_tick_thread()
            self.emit_event("play", self._book)
        elif event == "state" and message == GstPlayerState.PAUSED:
            self._stop_tick_thread()
            self.emit_event("pause")
        elif event == "state" and message == GstPlayerState.STOPPED:
            self._book = None
            self._stop_tick_thread()
            self.emit_event("pause")
            self.emit_event("stop")

    def _finish_book(self):
        if self._book:
            self._book.position = -1
            self._library.last_played_book = None

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

    def _fadeout_playback(self):
        duration = self._app_settings.sleep_timer_fadeout_duration * 20
        current_vol = self._gst_player.volume
        for i in range(0, duration):
            volume = max(current_vol - (i / duration), 0)
            self._gst_player.position = volume
            time.sleep(0.05)

        log.info("Fadeout completed.")
        self.play_pause()
        self._gst_player.volume = current_vol
        self.emit_event("fadeout-finished", None)

        self._fadeout_thread = None

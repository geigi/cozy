import logging
import os
import time
from threading import Thread
from typing import Optional
from cozy.media.importer import Importer, ScanStatus

from gi.repository import GLib, Gst

from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.control.offline_cache import OfflineCache
from cozy.ext import inject
from cozy.media.gst_player import GstPlayer, GstPlayerState
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library
from cozy.report import reporter
from cozy.tools import IntervalTimer
from cozy.ui.file_not_found_dialog import FileNotFoundDialog
from cozy.ui.info_banner import InfoBanner

log = logging.getLogger("mediaplayer")

NS_TO_SEC = 10 ** 9
REWIND_SECONDS = 30


class Player(EventSender):
    _library: Library = inject.attr(Library)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _offline_cache: OfflineCache = inject.attr(OfflineCache)
    _info_bar: InfoBanner = inject.attr(InfoBanner)
    _importer: Importer = inject.attr(Importer)

    _gst_player: GstPlayer = inject.attr(GstPlayer)

    def __init__(self):
        super().__init__()

        self._book: Optional[Book] = None
        self._play_next_chapter: bool = True

        self._importer.add_listener(self._on_importer_event)
        self._gst_player.add_listener(self._on_gst_player_event)

        self.play_status_updater: IntervalTimer = IntervalTimer(1, self._emit_tick)
        self._fadeout_thread: Optional[Thread] = None

        self._gst_player.init()
        self.volume = self._app_settings.volume

        self._load_last_book()

    def _load_last_book(self):
        last_book = self._library.last_played_book

        if last_book:
            self._continue_book(last_book)
            self._rewind_feature()

    @property
    def loaded_book(self) -> Optional[Book]:
        return self._book

    @property
    def loaded_chapter(self) -> Optional[Chapter]:
        if self._book:
            return self._book.current_chapter
        else:
            return None

    @property
    def playing(self) -> bool:
        return self._gst_player.state == GstPlayerState.PLAYING

    @property
    def position(self) -> int:
        return self._gst_player.position

    @position.setter
    def position(self, new_value: int):
        self._gst_player.position = self.loaded_chapter.start_position + (new_value * NS_TO_SEC)

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
            self._continue_book(book)
            self._gst_player.play()

    def play_pause_chapter(self, book: Book, chapter: Chapter):
        if not book or not chapter:
            log.error("Cannot play chapter which is None.")
            reporter.error("player", "Cannot play chapter which is None.")
            return

        if self._book and self._book.current_chapter == chapter:
            self.play_pause()
            return

        if self._book != book:
            self._load_book(book)

        self._load_chapter(chapter)
        self._gst_player.play()

        book.position = chapter.id

    def rewind(self, duration=None):
        state = self._gst_player.state
        if state != GstPlayerState.STOPPED:
            self._rewind_in_book(duration)
        if state == GstPlayerState.PLAYING:
            self._gst_player.play()

    def forward(self, duration=None):
        state = self._gst_player.state
        if state != GstPlayerState.STOPPED:
            self._forward_in_book(duration)
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

    def _continue_book(self, book: Book):
        if self._book == book:
            log.info("Not loading new book because it's unchanged.")
            return

        self._load_book(book)
        self._load_chapter(book.current_chapter)

    def _load_chapter(self, chapter: Chapter):
        file_changed = False

        if not self._book:
            log.error("There is no book loaded but there should be.")
            reporter.error("player", "There is no book loaded but there should be.")
            return

        self._library.last_played_book = self._book
        media_file_path = self._get_playback_path(chapter)

        if self._gst_player.loaded_file_path == media_file_path:
            log.info("Not loading a new file because the new chapter is within the old file.")
        else:
            log.info("Loading new file for chapter.")
            try:
                self._gst_player.load_file(media_file_path)
                file_changed = True
            except FileNotFoundError:
                self._handle_file_not_found()
                return

        if file_changed or self._should_jump_to_chapter_position(chapter.position):
            self._gst_player.position = chapter.position
            self._gst_player.playback_speed = self._book.playback_speed

        if file_changed or self._book.position != chapter.id:
            self._book.position = chapter.id
            self.emit_event_main_thread("chapter-changed", self._book)

    def _get_playback_path(self, chapter: Chapter):
        if self._book.offline and self._book.downloaded:
            path = self._offline_cache.get_cached_path(chapter)

            if path and os.path.exists(path):
                return path

        return chapter.file

    def _rewind_in_book(self, rewind_duration=None):
        if not self._book:
            log.error("Rewind in book not possible because no book is loaded.")
            reporter.error("player", "Rewind in book not possible because no book is loaded.")
            return

        if rewind_duration == None:
            rewind_duration = self._app_settings.rewind_duration

        current_position = self._gst_player.position
        current_position_relative = max(current_position - self.loaded_chapter.start_position, 0)
        chapter_number = self._book.chapters.index(self._book.current_chapter)
        rewind_seconds = rewind_duration * self.playback_speed

        if current_position_relative / NS_TO_SEC - rewind_seconds > 0:
            self._gst_player.position = current_position - NS_TO_SEC * rewind_seconds
        elif chapter_number > 0:
            previous_chapter = self._book.chapters[chapter_number - 1]
            self._load_chapter(previous_chapter)
            self._gst_player.position = previous_chapter.end_position + (
                        current_position_relative - NS_TO_SEC * rewind_seconds)
        else:
            self._gst_player.position = 0

    def _forward_in_book(self, forward_duration=None):
        if not self._book:
            log.error("Forward in book not possible because no book is loaded.")
            reporter.error("player", "Forward in book not possible because no book is loaded.")
            return

        if forward_duration == None:
            forward_duration = self._app_settings.forward_duration

        current_position = self._gst_player.position
        current_position_relative = max(current_position - self.loaded_chapter.start_position, 0)
        old_chapter = self._book.current_chapter
        chapter_number = self._book.chapters.index(self._book.current_chapter)
        forward_seconds = forward_duration * self.playback_speed

        if current_position_relative / NS_TO_SEC + forward_seconds < self._book.current_chapter.length:
            self._gst_player.position = current_position + (NS_TO_SEC * forward_seconds)
        elif chapter_number < len(self._book.chapters) - 1:
            next_chapter = self._book.chapters[chapter_number + 1]
            self._load_chapter(next_chapter)
            self._gst_player.position = next_chapter.start_position + (
                    NS_TO_SEC * forward_seconds - (old_chapter.length * NS_TO_SEC - current_position_relative))
        else:
            self._next_chapter()

    def _rewind_feature(self):
        if self._app_settings.replay:
            self._rewind_in_book()
            self._emit_tick()

    def _next_chapter(self):
        if not self._book:
            log.error("Cannot play next chapter because no book reference is stored.")
            reporter.error("player", "Cannot play next chapter because no book reference is stored.")

        index_current_chapter = self._book.chapters.index(self._book.current_chapter)

        self._book.current_chapter.position = self._book.current_chapter.start_position
        if len(self._book.chapters) <= index_current_chapter + 1:
            log.info("Book finished, stopping playback.")
            self._finish_book()
            self._gst_player.stop()
        else:
            chapter = self._book.chapters[index_current_chapter + 1]
            chapter.position = chapter.start_position
            self.play_pause_chapter(self._book, chapter)

    def _on_importer_event(self, event: str, message):
        if event == "scan" and message == ScanStatus.SUCCESS:
            log.info("Reloading current book")
            last_book = self._library.last_played_book
            if last_book:
                self._continue_book(last_book)
                # we need to tell everybody the new book object
                # it represents the same book but after a scan the old objects do get destroyed
                self.emit_event_main_thread("chapter-changed", self._book)

    def _on_gst_player_event(self, event: str, message):
        if event == "file-finished":
            self._next_chapter()
        elif event == "resource-not-found":
            self._handle_file_not_found()
        elif event == "state" and message == GstPlayerState.PLAYING:
            self._book.last_played = int(time.time())
            self._start_tick_thread()
            self.emit_event_main_thread("play", self._book)
        elif event == "state" and message == GstPlayerState.PAUSED:
            self._stop_tick_thread()
            self.emit_event_main_thread("pause")
        elif event == "state" and message == GstPlayerState.STOPPED:
            self._stop_playback()
        elif event == "error":
            self._handle_gst_error(message)

    def _handle_gst_error(self, error: GLib.Error):
        if error.code != Gst.ResourceError.BUSY:
            self._info_bar.show(error.message)

        if error.code == Gst.ResourceError.OPEN_READ or Gst.ResourceError.READ:
            self._stop_playback()

    def _handle_file_not_found(self):
        if self.loaded_chapter:
            FileNotFoundDialog(self.loaded_chapter).show()
            self._stop_playback()
        else:
            log.warning("No chapter loaded, cannot display file not found dialog.")

    def _stop_playback(self):
        self._stop_tick_thread()
        self._book = None
        self.emit_event_main_thread("pause")
        self.emit_event_main_thread("stop")

    def _finish_book(self):
        if self._book:
            self._book.position = -1
            self._library.last_played_book = None

        self.emit_event_main_thread("book-finished", self._book)

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
        if not self.loaded_chapter or not self.loaded_book:
            log.info("Not emitting tick because no book/chapter is loaded.")
            return

        if self.position > self.loaded_chapter.end_position:
            self._next_chapter()

        try:
            self.loaded_chapter.position = self.position
            position_for_ui = self.position - self.loaded_chapter.start_position
            self.emit_event_main_thread("position", position_for_ui)
        except Exception as e:
            log.warning("Could not emit position event: {}".format(e))

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
        self.emit_event_main_thread("fadeout-finished", None)

        self._fadeout_thread = None

    def _should_jump_to_chapter_position(self, position: int) -> bool:
        """
        Should the player jump to the given position?
        This allows gapless playback for media files that contain many chapters.
        """

        difference = abs(self.position - position)
        if difference < 10 ** 9:
            return False

        return True

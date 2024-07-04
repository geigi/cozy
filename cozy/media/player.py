import logging
import os
import time
from threading import Thread
from typing import Optional

from gi.repository import GLib, Gst

from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.control.offline_cache import OfflineCache
from cozy.ext import inject
from cozy.media.importer import Importer, ScanStatus
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library
from cozy.report import reporter
from cozy.tools import IntervalTimer
from cozy.ui.file_not_found_dialog import FileNotFoundDialog
from cozy.ui.toaster import ToastNotifier


import threading
from enum import Enum, auto
from typing import Optional

from gi.repository import Gst

from cozy.architecture.event_sender import EventSender
from cozy.report import reporter

log = logging.getLogger(__name__)

NS_TO_SEC = Gst.SECOND
US_TO_SEC = 1e6


class GstPlayer(EventSender):
    _bus: Gst.Bus | None
    _player: Gst.Bin | None

    def __init__(self):
        super().__init__()

        self._playback_speed: float = 1.0
        self._playback_speed_timer_running: bool = False
        self._volume: float = 1.0

        Gst.init(None)
        self.setup_pipeline()

    def setup_pipeline(self):
        scaletempo = Gst.ElementFactory.make("scaletempo", "scaletempo")
        scaletempo.sync_state_with_parent()

        audiobin = Gst.ElementFactory.make("bin", "audiosink")
        audiobin.add(scaletempo)

        audiosink = Gst.ElementFactory.make("autoaudiosink", "audiosink")
        audiobin.add(audiosink)

        scaletempo.link(audiosink)
        pad = scaletempo.get_static_pad("sink")
        ghost_pad = Gst.GhostPad.new("sink", pad)
        audiobin.add_pad(ghost_pad)

        self._player = Gst.ElementFactory.make("playbin", "player")
        self._player.set_property("audio-sink", audiobin)

        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._on_gst_message)

    @property
    def position(self) -> int:
        """Returns the player position in nanoseconds"""

        if not self._is_player_loaded():
            return 0

        position = self._query_gst_time(self._player.query_position)

        if position:
            return position

        log.warning("Failed to query position from player.")
        reporter.warning("gst_player", "Failed to query position from player.")

        return 0

    @position.setter
    def position(self, new_position_ns: int):
        """Sets the player position in nanoseconds"""

        if new_position_ns != 0:
            new_position_ns = max(0, new_position_ns)
            duration = self._query_gst_time(self._player.query_duration)

            if duration:
                new_position_ns = min(new_position_ns, duration)

        self._execute_seek(new_position_ns)

    @property
    def playback_speed(self) -> float:
        return self._playback_speed

    @playback_speed.setter
    def playback_speed(self, value: float):
        if not self._is_player_loaded():
            return

        self._playback_speed = value

        if self._playback_speed_timer_running:
            return

        self._playback_speed_timer_running = True

        t = threading.Timer(0.2, self._on_playback_speed_timer)
        t.name = "PlaybackSpeedDelayTimer"
        t.start()

    @property
    def loaded_file_path(self) -> Optional[str]:
        if not self._is_player_loaded():
            return None

        uri = self._player.get_property("current-uri")
        if uri:
            return uri.replace("file://", "")
        else:
            return None

    @property
    def state(self) -> Gst.State:
        if not self._is_player_loaded():
            return Gst.State.READY

        _, state, __ = self._player.get_state(Gst.CLOCK_TIME_NONE)
        if state == Gst.State.PLAYING:
            return Gst.State.PLAYING
        elif state == Gst.State.PAUSED:
            return Gst.State.PAUSED
        else:
            log.debug("GST player state was not playing or paused but %s", state)
            return Gst.State.READY

    @property
    def volume(self) -> float:
        if not self._is_player_loaded():
            log.error("Could not determine volume because player is not loaded.")
            return 1.0

        return self._player.get_property("volume")

    @volume.setter
    def volume(self, new_value: float):
        self._volume = max(0.0, min(1.0, new_value))

        if not self._is_player_loaded():
            log.warning("Could not set volume because player is not loaded.")
            return

        self._player.set_property("volume", self._volume)
        self._player.set_property("mute", False)

    def dispose(self):
        if not self._player:
            return

        self._player.set_state(Gst.State.NULL)
        self._playback_speed = 1.0
        log.info("Dispose")

    def load_file(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError()

        self._player.set_state(Gst.State.NULL)
        self._playback_speed = 1.0
        self._player.set_property("uri", "file://" + path)
        self._player.set_property("volume", self._volume)
        self._player.set_property("mute", False)
        self._player.set_state(Gst.State.PAUSED)

    def play(self):
        if not self._is_player_loaded() or self.state == Gst.State.PLAYING:
            return

        success = self._player.set_state(Gst.State.PLAYING)

        if success == Gst.StateChangeReturn.FAILURE:
            log.warning("Failed set gst player to play.")
            reporter.warning("gst_player", "Failed set gst player to play.")
        else:
            self.emit_event("state", Gst.State.PLAYING)

    def pause(self):
        if not self._is_player_loaded():
            return

        success = self._player.set_state(Gst.State.PAUSED)

        if success == Gst.StateChangeReturn.FAILURE:
            log.warning("Failed set gst player to pause.")
            reporter.warning("gst_player", "Failed set gst player to pause.")
        else:
            self.emit_event("state", Gst.State.PAUSED)

    def stop(self):
        if not self._is_player_loaded():
            return

        self.dispose()
        self.emit_event("state", Gst.State.READY)

    def _is_player_loaded(self) -> bool:
        _, state, __ = self._player.get_state(Gst.CLOCK_TIME_NONE)
        return state in (Gst.State.PLAYING, Gst.State.PAUSED)

    @staticmethod
    def _query_gst_time(query_function) -> Optional[int]:
        success = False
        counter = 0

        while not success and counter < 10:
            success, value = query_function(Gst.Format.TIME)

            if success:
                return value
            else:
                counter += 1
                time.sleep(0.01)

        return None

    def _execute_seek(self, new_position_ns: int):
        counter = 0
        seeked = False
        while not seeked and counter < 500:
            seeked = self._player.seek(self._playback_speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH, Gst.SeekType.SET,
                                       new_position_ns, Gst.SeekType.NONE, 0)

            if not seeked:
                counter += 1
                time.sleep(0.01)
        if not seeked:
            log.info("Failed to seek, counter expired.")
            reporter.warning("gst_player", "Failed to seek, counter expired.")

    def _on_playback_speed_timer(self):
        self._player.seek(self._playback_speed, Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                          Gst.SeekType.SET, self.position, Gst.SeekType.NONE, 0)

        self._playback_speed_timer_running = False

    def _on_gst_message(self, _, message: Gst.Message):
        t = message.type
        if t == Gst.MessageType.BUFFERING:
            if message.percentage < 100:
                self._player.set_state(Gst.State.PAUSED)
                log.info("Buffering…")
            else:
                self._player.set_state(Gst.State.PLAYING)
                log.info("Buffering finished.")
        elif t == Gst.MessageType.EOS:
            self.emit_event("file-finished")
        elif t == Gst.MessageType.ERROR:
            error, debug_msg = message.parse_error()

            if error.code == Gst.ResourceError.NOT_FOUND:
                self.stop()
                self.emit_event("resource-not-found")

                log.warning("gst: Resource not found. Stopping player.")
                reporter.warning("gst_player", "gst: Resource not found. Stopping player.")
                return

            reporter.error("player", f"{error.code}: {error}")
            log.error("%s: %s", error.code, error)
            log.debug(debug_msg)
            self.emit_event("error", error)


class Player(EventSender):
    _library: Library = inject.attr(Library)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _offline_cache: OfflineCache = inject.attr(OfflineCache)
    _toast: ToastNotifier = inject.attr(ToastNotifier)
    _importer: Importer = inject.attr(Importer)

    def __init__(self):
        super().__init__()

        self._book: Optional[Book] = None
        self._play_next_chapter: bool = True

        self._gst_player = GstPlayer()

        self._importer.add_listener(self._on_importer_event)
        self._gst_player.add_listener(self._on_gst_player_event)

        self.play_status_updater: IntervalTimer = IntervalTimer(1, self._emit_tick)
        self._fadeout_thread: Optional[Thread] = None

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
        return self._gst_player.state == Gst.State.PLAYING

    @property
    def position(self) -> int:
        return self._gst_player.position

    @position.setter
    def position(self, new_value: int):
        # FIXME: setter expects seconds, but getter returns nanoseconds
        if self.loaded_chapter is not None:
            self._gst_player.position = max(self.loaded_chapter.start_position + new_value * Gst.SECOND, 0)

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
        if self._gst_player.state == Gst.State.PAUSED:
            self._gst_player.play()
        elif self._gst_player.state == Gst.State.PLAYING:
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

        if self._gst_player.state == Gst.State.PLAYING:
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

    def rewind(self):
        state = self._gst_player.state
        if state != Gst.State.READY:
            self._rewind_in_book()
        if state == Gst.State.PLAYING:
            self._gst_player.play()

    def forward(self):
        state = self._gst_player.state
        if state != Gst.State.READY:
            self._forward_in_book()
        if state == Gst.State.PLAYING:
            self._gst_player.play()

    def destroy(self):
        self._gst_player.dispose()
        self._stop_playback()

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
            self._gst_player.playback_speed = self._book.playback_speed
            self._gst_player.position = chapter.position

        if file_changed or self._book.position != chapter.id:
            self._book.position = chapter.id
            self.emit_event_main_thread("chapter-changed", self._book)

    def _get_playback_path(self, chapter: Chapter):
        if self._book.offline and self._book.downloaded:
            path = self._offline_cache.get_cached_path(chapter)

            if path and os.path.exists(path):
                return path

        return chapter.file

    def _rewind_in_book(self):
        if not self._book:
            log.error("Rewind in book not possible because no book is loaded.")
            reporter.error("player", "Rewind in book not possible because no book is loaded.")
            return

        current_position = self._gst_player.position
        current_position_relative = max(current_position - self.loaded_chapter.start_position, 0)
        chapter_number = self._book.chapters.index(self._book.current_chapter)
        rewind_seconds = self._app_settings.rewind_duration * self.playback_speed

        if current_position_relative / NS_TO_SEC - rewind_seconds > 0:
            self._gst_player.position = current_position - NS_TO_SEC * rewind_seconds
        elif chapter_number > 0:
            previous_chapter = self._book.chapters[chapter_number - 1]
            self._load_chapter(previous_chapter)
            self._gst_player.position = previous_chapter.end_position + (
                        current_position_relative - NS_TO_SEC * rewind_seconds)
        else:
            self._gst_player.position = 0

    def _forward_in_book(self):
        if not self._book:
            log.error("Forward in book not possible because no book is loaded.")
            reporter.error("player", "Forward in book not possible because no book is loaded.")
            return

        current_position = self._gst_player.position
        current_position_relative = max(current_position - self.loaded_chapter.start_position, 0)
        old_chapter = self._book.current_chapter
        chapter_number = self._book.chapters.index(self._book.current_chapter)
        forward_seconds = self._app_settings.forward_duration * self.playback_speed

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
            return

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
        elif event == "state" and message == Gst.State.PLAYING:
            self._book.last_played = int(time.time())
            self._start_tick_thread()
            self.emit_event_main_thread("play", self._book)
        elif event == "state" and message == Gst.State.PAUSED:
            self._stop_tick_thread()
            self.emit_event_main_thread("pause")
        elif event == "state" and message == Gst.State.READY:
            self._stop_playback()
        elif event == "error":
            self._handle_gst_error(message)

    def _handle_gst_error(self, error: GLib.Error):
        if error.code != Gst.ResourceError.BUSY:
            self._toast.show(error.message)

        if error.code == Gst.ResourceError.OPEN_READ or Gst.ResourceError.READ:
            self._stop_playback()

    def _handle_file_not_found(self):
        if self.loaded_chapter:
            FileNotFoundDialog(self.loaded_chapter).present()
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
            log.warning("Could not emit position event: %s", e)

    def _fadeout_playback(self):
        duration = self._app_settings.sleep_timer_fadeout_duration * 20
        current_vol = self._gst_player.volume
        for i in range(duration):
            volume = max(current_vol - (i / duration), 0)
            self._gst_player.volume = volume
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

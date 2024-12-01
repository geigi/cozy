import logging
import os
import time
from typing import Optional

import inject
from gi.repository import GLib, Gst, GstController, Gtk

from cozy.architecture.event_sender import EventSender
from cozy.control.offline_cache import OfflineCache
from cozy.media.importer import Importer, ScanStatus
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.model.library import Library
from cozy.report import reporter
from cozy.settings import ApplicationSettings
from cozy.tools import IntervalTimer
from cozy.ui.file_not_found_dialog import FileNotFoundDialog
from cozy.ui.toaster import ToastNotifier

log = logging.getLogger(__name__)


class GstPlayer(EventSender):
    _player: Gst.Bin

    def __init__(self):
        super().__init__()

        self._playback_speed: float = 1.0
        self._playback_speed_timer_running: bool = False
        self._volume: float = 1.0
        self._fade_timeout: int | None = None

        self._setup_pipeline()
        self._setup_fadeout_control()

        bus = self._player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_gst_message)

    def _setup_pipeline(self):
        Gst.init(None)

        audio_sink = Gst.Bin.new()

        scaletempo = Gst.ElementFactory.make("scaletempo", "scaletempo")
        scaletempo.sync_state_with_parent()

        self._volume_fader = Gst.ElementFactory.make("volume", "fadevolume")
        audiosink = Gst.ElementFactory.make("autoaudiosink", "autoaudiosink")

        audio_sink.add(self._volume_fader)
        audio_sink.add(scaletempo)
        audio_sink.add(audiosink)

        self._volume_fader.link(scaletempo)
        scaletempo.link(audiosink)

        ghost_pad = Gst.GhostPad.new("sink", self._volume_fader.get_static_pad("sink"))
        audio_sink.add_pad(ghost_pad)

        self._player = Gst.ElementFactory.make("playbin", "player")
        self._player.set_property("audio-sink", audio_sink)

    def _setup_fadeout_control(self):
        self.fadeout_control_source = GstController.InterpolationControlSource(
            mode=GstController.InterpolationMode.LINEAR
        )

        fadeout_control_binding = GstController.DirectControlBinding(
            object=self._volume_fader,
            name="volume",
            absolute=True,
            control_source=self.fadeout_control_source,
        )

        self._volume_fader.add_control_binding(fadeout_control_binding)

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

        GLib.timeout_add(200, self._on_playback_speed_timer)

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
        return self._player.get_property("volume")

    @volume.setter
    def volume(self, new_value: float):
        self._volume = max(0.0, min(1.0, new_value))
        self._player.set_property("volume", self._volume)
        self._player.set_property("mute", False)

    def load_file(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError()

        self._player.set_state(Gst.State.NULL)
        self._playback_speed = 1.0
        self._player.set_property("uri", "file://" + path)
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

        self._player.set_state(Gst.State.NULL)
        self._playback_speed = 1.0

        self.emit_event("state", Gst.State.READY)

    def _fadeout_callback(self) -> None:
        self.fadeout_control_source.unset_all()

        if self._fade_timeout:
            GLib.source_remove(self._fade_timeout)
            self._fade_timeout = None

        self._volume_fader.props.volume = 1.0

    def fadeout(self, length: int) -> None:
        if not self._is_player_loaded():
            return

        position = self._query_gst_time(self._player.query_position)
        duration = self._query_gst_time(self._player.query_duration)

        if position is None or duration is None:
            return

        end_position = min(position + length * Gst.SECOND, duration)

        log.info("Starting playback fadeout")

        self.fadeout_control_source.set(position, 1.0)
        self.fadeout_control_source.set(end_position, 0.0)

        self._fade_timeout = GLib.timeout_add(
            (end_position - position) // Gst.MSECOND, self._fadeout_callback
        )

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
            seeked = self._player.seek(
                self._playback_speed,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH,
                Gst.SeekType.SET,
                new_position_ns,
                Gst.SeekType.NONE,
                0,
            )

            if not seeked:
                counter += 1
                time.sleep(0.01)
        if not seeked:
            log.info("Failed to seek, counter expired.")
            reporter.warning("gst_player", "Failed to seek, counter expired.")

    def _on_playback_speed_timer(self):
        self._player.seek(
            self._playback_speed,
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET,
            self.position,
            Gst.SeekType.NONE,
            0,
        )

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


class PowerManager:
    _gtk_app = inject.attr("GtkApp")

    def __init__(self):
        self._inhibit_cookie = None

    def _on_player_changed(self, event: str, data):
        if event in ["pause", "stop"]:
            if self._inhibit_cookie:
                log.info("Uninhibited standby.")
                self._gtk_app.uninhibit(self._inhibit_cookie)
                self._inhibit_cookie = None

        elif event == "play":
            if self._inhibit_cookie:
                return

            self._inhibit_cookie = self._gtk_app.inhibit(
                None, Gtk.ApplicationInhibitFlags.SUSPEND, "Playback of audiobook"
            )
            log.info("Inhibited standby.")


class Player(EventSender):
    _library: Library = inject.attr(Library)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _offline_cache: OfflineCache = inject.attr(OfflineCache)
    _toast: ToastNotifier = inject.attr(ToastNotifier)
    _importer: Importer = inject.attr(Importer)
    _gst_player: GstPlayer = inject.attr(GstPlayer)

    def __init__(self):
        super().__init__()

        self._book: Optional[Book] = None
        self._play_next_chapter: bool = True

        self.add_listener(PowerManager()._on_player_changed)
        self._importer.add_listener(self._on_importer_event)
        self._gst_player.add_listener(self._on_gst_player_event)

        self.play_status_updater: IntervalTimer = IntervalTimer(1, self._emit_tick)

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
        if self.loaded_chapter is not None:
            self._gst_player.position = max(self.loaded_chapter.start_position + new_value, 0)

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

    def fadeout(self, duration: int):
        self._gst_player.fadeout(duration)

    def pause(self):
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

    def volume_up(self):
        self.volume = min(1.0, self.volume + 0.1)

    def volume_down(self):
        self.volume = max(0, self.volume - 0.1)

    def destroy(self):
        self._gst_player.stop()

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

            if path and path.exists():
                return str(path)

        return chapter.file

    def _rewind_in_book(self):
        if not self._book:
            log.error("Rewind in book not possible because no book is loaded.")
            reporter.error("player", "Rewind in book not possible because no book is loaded.")
            return

        current_position = self._gst_player.position
        current_position_relative = max(current_position - self.loaded_chapter.start_position, 0)
        chapter_number = self._book.chapters.index(self._book.current_chapter)
        rewind_nanoseconds = self._app_settings.rewind_duration * Gst.SECOND * self.playback_speed

        if current_position_relative - rewind_nanoseconds > 0:
            self._gst_player.position = current_position - rewind_nanoseconds
        elif chapter_number > 0:
            previous_chapter = self._book.chapters[chapter_number - 1]
            self._load_chapter(previous_chapter)
            self._gst_player.position = previous_chapter.end_position + (
                current_position_relative - rewind_nanoseconds
            )
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
        forward_nanoseconds = self._app_settings.forward_duration * Gst.SECOND * self.playback_speed

        if current_position_relative + forward_nanoseconds < self._book.current_chapter.length:
            self._gst_player.position = current_position + forward_nanoseconds
        elif chapter_number < len(self._book.chapters) - 1:
            next_chapter = self._book.chapters[chapter_number + 1]
            self._load_chapter(next_chapter)
            self._gst_player.position = next_chapter.start_position + (
                forward_nanoseconds - old_chapter.length - current_position_relative
            )
        else:
            self._next_chapter()

    def _rewind_feature(self):
        if self._app_settings.replay:
            self._rewind_in_book()
            self._emit_tick()

    def _next_chapter(self):
        if not self._book:
            log.error("Cannot play next chapter because no book reference is stored.")
            reporter.error(
                "player", "Cannot play next chapter because no book reference is stored."
            )
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

    def _previous_chapter(self):
        if not self._book:
            log.error("Cannot play previous chapter because no book reference is stored.")
            reporter.error(
                "player", "Cannot play previous chapter because no book reference is stored."
            )
            return

        index_current_chapter = self._book.chapters.index(self._book.current_chapter)
        self._book.current_chapter.position = self._book.current_chapter.start_position

        if index_current_chapter - 1 < 0:
            log.info("Book reached start, cannot rewind further.")
            chapter = self._book.chapters[0]
            chapter.position = chapter.start_position

            self._load_chapter(chapter)
            self.pause()
            self._emit_tick()
        else:
            chapter = self._book.chapters[index_current_chapter - 1]
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
            if self._play_next_chapter:
                self._next_chapter()
            else:
                self._stop_playback()
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

        if self.position > self.loaded_chapter.end_position and self._play_next_chapter:
            self._next_chapter()

        try:
            self.loaded_chapter.position = self.position
            position_for_ui = self.position - self.loaded_chapter.start_position
            self.emit_event_main_thread("position", position_for_ui)
        except Exception as e:
            log.warning("Could not emit position event: %s", e)

    def _should_jump_to_chapter_position(self, position: int) -> bool:
        """
        Should the player jump to the given position?
        This allows gapless playback for media files that contain many chapters.
        """

        return not abs(self.position - position) < Gst.SECOND

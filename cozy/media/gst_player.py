import logging
import os
import threading
import time
from enum import Enum, auto
from typing import Optional

from cozy.architecture.event_sender import EventSender
from cozy.report import reporter

from gi.repository import Gst

log = logging.getLogger("gst_player")


class GstPlayerState(Enum):
    STOPPED = auto()
    PAUSED = auto()
    PLAYING = auto()


class GstPlayer(EventSender):
    def __init__(self):
        super().__init__()

        self._bus: Optional[Gst.Bus] = None
        self._player: Optional[Gst.Bin] = None
        self._bus_signal_id: Optional[int] = None
        self._playback_speed: float = 1.0
        self._playback_speed_timer_running: bool = False
        self._volume: float = 1.0

        Gst.init(None)

    @property
    def position(self) -> int:
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
    def state(self) -> GstPlayerState:
        if not self._is_player_loaded():
            return GstPlayerState.STOPPED

        _, state, __ = self._player.get_state(Gst.CLOCK_TIME_NONE)
        if state == Gst.State.PLAYING:
            return GstPlayerState.PLAYING
        elif state == Gst.State.PAUSED:
            return GstPlayerState.PAUSED
        else:
            log.debug("GST player state was not playing or paused but %s", state)
            return GstPlayerState.STOPPED

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

    def init(self):
        if self._player:
            self.dispose()

        self._player = Gst.ElementFactory.make("playbin", "player")
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

        self._player.set_property("audio-sink", audiobin)

        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._bus_signal_id = self._bus.connect("message", self._on_gst_message)

    def dispose(self):
        if not self._player:
            return

        if self._bus_signal_id:
            self._bus.disconnect(self._bus_signal_id)

        self._player.set_state(Gst.State.NULL)
        self._playback_speed = 1.0
        log.info("Dispose")
        self.emit_event("dispose")

    def load_file(self, path: str):
        self.init()

        if not os.path.exists(path):
            raise FileNotFoundError()

        self._player.set_property("uri", "file://" + path)
        self._player.set_state(Gst.State.PAUSED)
        self._player.set_property("volume", self._volume)
        self._player.set_property("mute", False)

    def play(self):
        if not self._is_player_loaded() or self.state == GstPlayerState.PLAYING:
            return

        success = self._player.set_state(Gst.State.PLAYING)

        if success == Gst.StateChangeReturn.FAILURE:
            log.warning("Failed set gst player to play.")
            reporter.warning("gst_player", "Failed set gst player to play.")
        else:
            self.emit_event("state", GstPlayerState.PLAYING)

    def pause(self):
        if not self._is_player_loaded():
            return

        success = self._player.set_state(Gst.State.PAUSED)

        if success == Gst.StateChangeReturn.FAILURE:
            log.warning("Failed set gst player to pause.")
            reporter.warning("gst_player", "Failed set gst player to pause.")
        else:
            self.emit_event("state", GstPlayerState.PAUSED)

    def stop(self):
        if not self._is_player_loaded():
            return

        self.dispose()
        self.emit_event("state", GstPlayerState.STOPPED)

    def _is_player_loaded(self) -> bool:
        if not self._player:
            return False

        _, state, __ = self._player.get_state(Gst.CLOCK_TIME_NONE)
        if state != Gst.State.PLAYING and state != Gst.State.PAUSED:
            return False

        return True

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

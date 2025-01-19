import logging
import os
from enum import Enum

import inject
from gi.repository import Gio, GLib, Gst

from cozy.architecture.observable import Observable
from cozy.media.player import Player
from cozy.settings import ApplicationSettings

log = logging.getLogger("sleep_timer_view_model")

FADEOUT_DURATION = 20


class SystemPowerAction(Enum):
    NONE = 0
    SUSPEND = 1
    SHUTDOWN = 2


class SleepTimerViewModel(Observable):
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()

        self._remaining_seconds: int = 0
        self._system_power_action = SystemPowerAction.NONE
        self._timer_running = False
        self._fadeout_running = False

        self._player.add_listener(self._on_player_changed)

    @property
    def timer_enabled(self) -> bool:
        return self.remaining_seconds > 0 or self.stop_after_chapter

    @property
    def remaining_seconds(self) -> int:
        return self._remaining_seconds

    @remaining_seconds.setter
    def remaining_seconds(self, new_value: int):
        self._remaining_seconds = new_value

        if new_value > 0:
            self._start_timer()
        else:
            self._stop_timer()

    @property
    def system_power_action(self) -> SystemPowerAction:
        return self._system_power_action

    @system_power_action.setter
    def system_power_action(self, new_value: SystemPowerAction) -> None:
        self._system_power_action = new_value

    @property
    def stop_after_chapter(self) -> bool:
        return not self._player.play_next_chapter

    @stop_after_chapter.setter
    def stop_after_chapter(self, new_value: bool):
        self._player.play_next_chapter = not new_value

        if new_value:
            self.remaining_seconds = 0
            log.info("Stop at end of Chapter Set")

        self._notify("remaining_seconds")
        self._notify("stop_after_chapter")
        self._notify("timer_enabled")

    def get_remaining_from_chapter(self) -> float | None:
        book = self._player.loaded_book
        if not book:
            return 0

        position = book.current_chapter.length - (
            book.current_chapter.position - book.current_chapter.start_position
        )
        return int(position / Gst.SECOND / book.playback_speed)

    def _start_timer(self):
        self.stop_after_chapter = False
        self._timer_running = True

        log.info("Start Sleep Timer")
        self._notify("timer_enabled")

    def _stop_timer(self):
        self._timer_running = False

        log.info("Stop Sleep Timer")
        self._notify("timer_enabled")

    def _on_timer_tick(self):
        self._remaining_seconds -= 1
        self._notify("remaining_seconds")

        if self._remaining_seconds <= FADEOUT_DURATION and not self._fadeout_running:
            self._fadeout_running = True
            self._player.fadeout(FADEOUT_DURATION)

        if self._remaining_seconds <= 0:
            self._stop_timer()
            self._player.pause()
            self._handle_system_power_event()

    def _on_player_changed(self, event, _):
        if event == "position":
            if self._timer_running:
                self._on_timer_tick()
        elif event == "chapter-changed":
            self.stop_after_chapter = False
        elif event == "fadeout-finished":
            self._handle_system_power_event()

    def _handle_system_power_event(self):
        match self.system_power_action:
            case SystemPowerAction.SHUTDOWN:
                self._shutdown()
            case SystemPowerAction.SUSPEND:
                self._suspend()
            case _:
                return

    def _shutdown(self):
        inject.instance("MainWindow").quit()  # Exit gracefully
        if os.getenv("XDG_CURRENT_DESKTOP") == "GNOME":
            Gio.bus_get_sync(Gio.BusType.SESSION, None).call_sync(
                "org.gnome.SessionManager",
                "/org/gnome/SessionManager",
                "org.gnome.SessionManager",
                "Shutdown",
                None,
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
        else:
            Gio.bus_get_sync(Gio.BusType.SYSTEM, None).call_sync(
                "org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager",
                "PowerOff",
                GLib.Variant.new_tuple(GLib.Variant.new_boolean(True)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )

    def _suspend(self):
        Gio.bus_get_sync(Gio.BusType.SYSTEM, None).call_sync(
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager",
            "Suspend",
            GLib.Variant.new_tuple(GLib.Variant.new_boolean(True)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )

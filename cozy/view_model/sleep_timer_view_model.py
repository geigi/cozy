import logging
import os
import sys
from enum import Enum, auto
from typing import Optional

import inject

from cozy.architecture.observable import Observable
from cozy.media.player import Player
from cozy.settings import ApplicationSettings
from cozy.tools import IntervalTimer

log = logging.getLogger("sleep_timer_view_model")

FADEOUT_DURATION = 20


class SystemPowerControl(Enum):
    OFF = auto()
    SUSPEND = auto()
    SHUTDOWN = auto()


class SleepTimerViewModel(Observable):
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()

        self._remaining_seconds: int = 0
        self._system_power_control: SystemPowerControl = SystemPowerControl.OFF
        self._sleep_timer: Optional[IntervalTimer] = None
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

        self._notify("timer_enabled")

    @property
    def system_power_control(self) -> SystemPowerControl:
        return self._system_power_control

    @system_power_control.setter
    def system_power_control(self, new_value: SystemPowerControl):
        self._system_power_control = new_value

    @property
    def stop_after_chapter(self) -> bool:
        return not self._player.play_next_chapter

    @stop_after_chapter.setter
    def stop_after_chapter(self, new_value: bool):
        self._player.play_next_chapter = not new_value

        if new_value:
            self._stop_timer()
            self.remaining_seconds = 0
            log.info("Sleep Timer Stop at end of Chapter Set")

        self._notify("remaining_seconds")
        self._notify("stop_after_chapter")
        self._notify("timer_enabled")

    def destroy(self):
        self._stop_timer()

    def _start_timer(self):
        self.stop_after_chapter = False
        if self._sleep_timer or self._remaining_seconds < 1 or not self._player.playing:
            return

        log.info("Start Sleep Timer")
        self._sleep_timer = IntervalTimer(1, self._on_timer_tick)
        self._sleep_timer.start()

    def _stop_timer(self):
        if not self._sleep_timer:
            return

        log.info("Stop Sleep Timer")
        self._sleep_timer.stop()
        self._sleep_timer = None
        self._notify("timer_enabled")

    def _stop_playback(self):
        self._player.pause()

    def _on_timer_tick(self):
        self._remaining_seconds -= 1

        if self._remaining_seconds <= FADEOUT_DURATION and not self._fadeout_running:
            self._fadeout_running = True
            self._player.fadeout(FADEOUT_DURATION)

        if self._remaining_seconds <= 0:
            self._stop_timer()
            self._stop_playback()

        self._notify_main_thread("remaining_seconds")

    def _on_player_changed(self, event, _):
        if event == "chapter-changed":
            self.stop_after_chapter = False
            self._notify("stop_after_chapter")
        elif event == "play":
            self._start_timer()
        elif event in {"pause", "stop"}:
            self._stop_timer()

    def _handle_system_power_event(self):
        # TODO: This doesn't work in Flatpak. Either remove it completely, or make it conditional'
        command = None

        if self.system_power_control == SystemPowerControl.SHUTDOWN:
            log.info("system will attempt to shutdown now!")
            if "linux" in sys.platform.lower():
                command = "systemctl poweroff"
            else:
                command = "shutdown -h now"
        elif self.system_power_control == SystemPowerControl.SUSPEND:
            log.info("system will attempt to suspend now!")
            if "linux" in sys.platform.lower():
                command = "systemctl suspend"

        if command:
            os.system(command)

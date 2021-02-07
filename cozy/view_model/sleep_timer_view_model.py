import logging
import os
from enum import Enum, auto
from typing import Optional

from cozy import tools
from cozy.application_settings import ApplicationSettings
from cozy.architecture.observable import Observable
from cozy.ext import inject
from cozy.media.player import Player
from cozy.tools import IntervalTimer

log = logging.getLogger("sleep_timer_view_model")


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
        self._wait_for_fadeout_end: bool = False

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
        self._stop_timer()
        self.remaining_seconds = 0
        self._notify("remaining_seconds")
        self._notify("timer_enabled")

    def destroy(self):
        self._stop_timer()

    def _start_timer(self):
        if self._sleep_timer:
            return

        if self.remaining_seconds < 1:
            return

        if not self._player.playing:
            return

        log.info("Start Timer")
        self._sleep_timer = tools.IntervalTimer(1, self._on_timer_tick)
        self._sleep_timer.start()

    def _stop_timer(self):
        if not self._sleep_timer:
            return

        log.info("Stop Timer")
        self._sleep_timer.stop()
        self._sleep_timer = None

    def _on_timer_tick(self):
        self.remaining_seconds = self.remaining_seconds - 1
        self._notify_main_thread("remaining_seconds")

        fadeout = self._get_fadeout()
        if self.remaining_seconds - fadeout < 1:
            self._stop_playback()
            self._stop_timer()
            self._notify("timer_enabled")

            if not self._wait_for_fadeout_end:
                self._handle_system_power_event()
            else:
                self.remaining_seconds = 0
                self._notify_main_thread("remaining_seconds")

    def _get_fadeout(self) -> int:
        fadeout = 0

        if self._app_settings.sleep_timer_fadeout:
            fadeout = self._app_settings.sleep_timer_fadeout_duration

        return fadeout

    def _stop_playback(self):
        fadeout = self._get_fadeout()
        self._wait_for_fadeout_end = fadeout > 0
        self._player.pause(fadeout=fadeout > 0)

    def _handle_system_power_event(self):
        platform = tools.system_platform()
        command = ""

        if self.system_power_control == SystemPowerControl.SHUTDOWN:
            log.info("system will attempt to shutdown now!")
            if platform is tools.Platform.Linux:
                command = "systemctl poweroff"
            else:
                command = "shutdown -h now"
        elif self.system_power_control == SystemPowerControl.SUSPEND:
            log.info("system will attempt to suspend now!")
            if platform is tools.Platform.Linux:
                command = "systemctl suspend"

        if command:
            os.system(command)

    def _on_player_changed(self, event, _):
        if event == "chapter-changed":
            self.stop_after_chapter = False
            self._notify("stop_after_chapter")
        elif event == "play":
            self._start_timer()
        elif event == "pause" or event == "stop":
            self._stop_timer()
        elif event == "fadeout-finished" and self._wait_for_fadeout_end:
            self._wait_for_fadeout_end = False
            self._handle_system_power_event()

import inject
from gi.repository import Gio

from cozy.architecture.event_sender import EventSender


class ApplicationSettings(EventSender):
    _settings: Gio.Settings = inject.attr(Gio.Settings)

    def __init__(self):
        super().__init__()
        self._settings.delay()
        self._connect()

    def _connect(self):
        self._settings.connect("changed", self._key_changed)

    def _key_changed(self, settings: Gio.Settings, key: str):
        self.emit_event(key)

    @property
    def hide_offline(self) -> bool:
        return self._settings.get_boolean("hide-offline")

    @hide_offline.setter
    def hide_offline(self, new_value: bool):
        self._settings.set_boolean("hide-offline", new_value)

    @property
    def swap_author_reader(self) -> bool:
        return self._settings.get_boolean("swap-author-reader")

    @property
    def volume(self) -> float:
        return self._settings.get_double("volume")

    @volume.setter
    def volume(self, new_value: float):
        self._settings.set_double("volume", new_value)

    @property
    def titlebar_remaining_time(self) -> bool:
        return self._settings.get_boolean("titlebar-remaining-time")

    @titlebar_remaining_time.setter
    def titlebar_remaining_time(self, new_value: bool):
        self._settings.set_boolean("titlebar-remaining-time", new_value)

    @property
    def replay(self) -> bool:
        return self._settings.get_boolean("replay")

    @property
    def autoscan(self) -> bool:
        return self._settings.get_boolean("autoscan")

    @property
    def prefer_external_cover(self) -> bool:
        return self._settings.get_boolean("prefer-external-cover")

    @prefer_external_cover.setter
    def prefer_external_cover(self, new_value: bool):
        self._settings.set_boolean("prefer-external-cover", new_value)

    @property
    def timer(self) -> int:
        return self._settings.get_int("timer")

    @timer.setter
    def timer(self, new_value: int):
        self._settings.set_int("timer", new_value)

    @property
    def report_level(self) -> int:
        return self._settings.get_int("report-level")

    @report_level.setter
    def report_level(self, new_value: int):
        self._settings.set_int("report-level", new_value)

    @property
    def last_launched_version(self) -> str:
        return self._settings.get_string("last-launched-version")

    @last_launched_version.setter
    def last_launched_version(self, new_value: str):
        self._settings.set_string("last-launched-version", new_value)

    @property
    def first_launch(self) -> bool:
        return self._settings.get_boolean("first-launch")

    @first_launch.setter
    def first_launch(self, new_value: bool):
        self._settings.set_boolean("first-launch", new_value)

    @property
    def rewind_duration(self) -> int:
        return self._settings.get_int("rewind-duration")

    @rewind_duration.setter
    def rewind_duration(self, new_value):
        self._settings.set_int("rewind-duration", new_value)

    @property
    def forward_duration(self) -> int:
        return self._settings.get_int("forward-duration")

    @forward_duration.setter
    def forward_duration(self, new_value):
        self._settings.set_int("forward-duration", new_value)

    @property
    def window_width(self) -> int:
        return self._settings.get_int("window-width")

    @window_width.setter
    def window_width(self, new_value: int):
        self._settings.set_int("window-width", new_value)

    @property
    def window_height(self) -> int:
        return self._settings.get_int("window-height")

    @window_height.setter
    def window_height(self, new_value: int):
        self._settings.set_int("window-height", new_value)

    @property
    def window_maximize(self) -> bool:
        return self._settings.get_boolean("window-maximize")

    @window_maximize.setter
    def window_maximize(self, new_value: bool):
        self._settings.set_boolean("window-maximize", new_value)

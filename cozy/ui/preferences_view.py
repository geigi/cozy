from typing import Any
from gi.repository import Adw, Gio, Gtk

from cozy.ext import inject
from cozy.ui.widgets.error_reporting import ErrorReporting

from cozy.ui.widgets.storages import StorageLocations
from cozy.view_model.settings_view_model import SettingsViewModel


@Gtk.Template.from_resource("/com/github/geigi/cozy/preferences.ui")
class PreferencesView(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    _glib_settings: Gio.Settings = inject.attr(Gio.Settings)
    _view_model: SettingsViewModel = inject.attr(SettingsViewModel)

    storages_page: Adw.PreferencesPage = Gtk.Template.Child()
    user_feedback_preference_group: Adw.PreferencesGroup = Gtk.Template.Child()

    swap_author_reader_switch: Adw.SwitchRow = Gtk.Template.Child()
    replay_switch: Adw.SwitchRow = Gtk.Template.Child()

    sleep_timer_fadeout_switch: Adw.SwitchRow = Gtk.Template.Child()
    artwork_prefer_external_switch: Adw.SwitchRow = Gtk.Template.Child()

    rewind_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    forward_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    fadeout_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    def __init__(self, **kwargs: Any) -> None:
        main_window = inject.instance("MainWindow")
        super().__init__(transient_for=main_window.window, **kwargs)

        error_reporting = ErrorReporting()
        error_reporting.show_header(False)
        self.user_feedback_preference_group.add(error_reporting)

        self.storage_locations_view = StorageLocations()
        self.storages_page.add(self.storage_locations_view)

        self._view_model.bind_to("lock_ui", self._on_lock_ui_changed)
        self._bind_settings()

    def _bind_settings(self) -> None:
        self._glib_settings.bind(
            "swap-author-reader",
            self.swap_author_reader_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        self._glib_settings.bind(
            "replay", self.replay_switch, "active", Gio.SettingsBindFlags.DEFAULT
        )
        self._glib_settings.bind(
            "rewind-duration",
            self.rewind_duration_adjustment,
            "value",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self._glib_settings.bind(
            "forward-duration",
            self.forward_duration_adjustment,
            "value",
            Gio.SettingsBindFlags.DEFAULT,
        )

        self._glib_settings.bind(
            "sleep-timer-fadeout",
            self.sleep_timer_fadeout_switch,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )

        self._glib_settings.bind(
            "sleep-timer-fadeout-duration",
            self.fadeout_duration_adjustment,
            "value",
            Gio.SettingsBindFlags.DEFAULT,
        )

        self._glib_settings.bind(
            "prefer-external-cover",
            self.artwork_prefer_external_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

    def _on_lock_ui_changed(self) -> None:
        self.storage_locations_view.set_sensitive(not self._view_model.lock_ui)

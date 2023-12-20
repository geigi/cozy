from gi.repository import Gtk
from cozy.view_model.settings_view_model import SettingsViewModel
from gi.repository import Adw, Gio
from typing import Callable

from cozy.ext import inject
from cozy.ui.widgets.error_reporting import ErrorReporting
from cozy.ui.widgets.storages import StorageLocations


@Gtk.Template.from_resource('/com/github/geigi/cozy/preferences.ui')
class PreferencesView(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    main_window = inject.attr("MainWindow")

    _glib_settings: Gio.Settings = inject.attr(Gio.Settings)
    _view_model: SettingsViewModel = inject.attr(SettingsViewModel)

    storages_page: Adw.PreferencesPage = Gtk.Template.Child()
    user_feedback_preference_group: Adw.PreferencesGroup = Gtk.Template.Child()

    dark_mode_switch: Adw.SwitchRow = Gtk.Template.Child()
    swap_author_reader_switch: Adw.SwitchRow = Gtk.Template.Child()
    replay_switch: Adw.SwitchRow = Gtk.Template.Child()
    sleep_timer_fadeout_switch: Adw.SwitchRow = Gtk.Template.Child()
    artwork_prefer_external_switch: Adw.SwitchRow = Gtk.Template.Child()

    rewind_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    forward_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    fadeout_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(transient_for=self.main_window.window, **kwargs)

        error_reporting = ErrorReporting()
        error_reporting.show_header(False)
        self.user_feedback_preference_group.add(error_reporting)

        self.storage_locations_view = StorageLocations()
        self.storages_page.add(self.storage_locations_view)

        self._bind_settings()

        self._view_model.bind_to("lock_ui", self._on_lock_ui_changed)

        self.connect("close-request", self._hide_window)

    def _bind_settings(self):
        self._glib_settings.bind("dark-mode", self.dark_mode_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("swap-author-reader", self.swap_author_reader_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("replay", self.replay_switch, "active", Gio.SettingsBindFlags.DEFAULT)
        self._glib_settings.bind("rewind-duration", self.rewind_duration_adjustment, "value",
                                 Gio.SettingsBindFlags.DEFAULT)
        self._glib_settings.bind("forward-duration", self.forward_duration_adjustment, "value",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("sleep-timer-fadeout", self.sleep_timer_fadeout_switch, "enable-expansion",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("sleep-timer-fadeout-duration", self.fadeout_duration_adjustment,
                                 "value", Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("prefer-external-cover", self.artwork_prefer_external_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

    def _on_lock_ui_changed(self):
        sensitive = not self._view_model.lock_ui

        self.storage_locations_view.set_sensitive(sensitive)
    
    def _hide_window(self, *_):
        self.hide()
        return True

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

    dark_mode_switch: Gtk.Switch = Gtk.Template.Child()
    swap_author_reader_switch: Gtk.Switch = Gtk.Template.Child()
    replay_switch: Gtk.Switch = Gtk.Template.Child()
    sleep_timer_fadeout_switch: Adw.SwitchRow = Gtk.Template.Child()
    fadeout_duration_spin_button: Adw.SpinRow = Gtk.Template.Child()
    artwork_prefer_external_switch: Gtk.Switch = Gtk.Template.Child()

    rewind_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    forward_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    fadeout_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    user_feedback_preference_group: Adw.PreferencesRow = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(transient_for=self.main_window.window, **kwargs)

        error_reporting = ErrorReporting()
        error_reporting.show_header(False)
        self.user_feedback_preference_group.add(error_reporting)

        storage_locations = StorageLocations()
        self.storages_page.add(storage_locations)

        self._bind_settings()

        self.connect("close-request", self._hide_window)

        self.sleep_timer_fadeout_switch.connect("notify::active", self._on_sleep_fadeout_switch_changed)
        self.fadeout_duration_spin_button.set_sensitive(self.sleep_timer_fadeout_switch.props.active)

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

        self._glib_settings.bind("sleep-timer-fadeout", self.sleep_timer_fadeout_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("sleep-timer-fadeout-duration", self.fadeout_duration_adjustment,
                                 "value", Gio.SettingsBindFlags.DEFAULT)

        self._glib_settings.bind("prefer-external-cover", self.artwork_prefer_external_switch, "active",
                                 Gio.SettingsBindFlags.DEFAULT)

    def _on_sleep_fadeout_switch_changed(self, widget, param):
        state = widget.get_property(param.name)
        self.fadeout_duration_spin_button.set_sensitive(state)
    
    def _on_lock_ui_changed(self):
        sensitive = not self._view_model.lock_ui

        self.storage_locations_list.set_sensitive(sensitive)
        self.add_storage_button.set_sensitive(sensitive)
        self.remove_storage_button.set_sensitive(sensitive)
        self.external_storage_toggle_button.set_sensitive(sensitive)
        self.default_storage_button.set_sensitive(sensitive)
        self._on_storage_box_changed(None, self.storage_locations_list.get_selected_row())
    
    def _hide_window(self, *_):
        self.hide()
        return True

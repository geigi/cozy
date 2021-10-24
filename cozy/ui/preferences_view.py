import gi
from gi.repository import Handy, Gio

from cozy.ext import inject
from cozy.ui.widgets.error_reporting import ErrorReporting

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/preferences.ui')
class PreferencesView(Handy.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    _glib_settings: Gio.Settings = inject.attr(Gio.Settings)

    dark_mode_switch: Gtk.Switch = Gtk.Template.Child()
    swap_author_reader_switch: Gtk.Switch = Gtk.Template.Child()
    replay_switch: Gtk.Switch = Gtk.Template.Child()
    sleep_timer_fadeout_switch: Gtk.Switch = Gtk.Template.Child()
    artwork_prefer_external_switch: Gtk.Switch = Gtk.Template.Child()

    rewind_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    forward_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    fadeout_duration_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    user_feedback_preference_group: Handy.PreferencesGroup = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        error_reporting = ErrorReporting()
        self.user_feedback_preference_group.add(error_reporting)

        self._bind_settings()

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

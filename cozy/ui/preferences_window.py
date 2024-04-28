from gi.repository import Adw, Gio, Gtk

from cozy.ext import inject
from cozy.ui.widgets.error_reporting import ErrorReporting
from cozy.ui.widgets.storages import StorageLocations
from cozy.view_model.settings_view_model import SettingsViewModel


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/preferences.ui")
class PreferencesWindow(Adw.PreferencesDialog):
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

    def __init__(self) -> None:
        super().__init__()

        error_reporting = ErrorReporting()
        error_reporting.show_header(False)
        self.user_feedback_preference_group.add(error_reporting)

        self.storage_locations_view = StorageLocations()
        self.storages_page.add(self.storage_locations_view)

        self._view_model.bind_to("lock_ui", self._on_lock_ui_changed)
        self._bind_settings()

    def _bind_settings(self) -> None:
        bind_settings = lambda setting, widget, propetry: self._glib_settings.bind(
            setting, widget, propetry, Gio.SettingsBindFlags.DEFAULT
        )

        bind_settings("swap-author-reader", self.swap_author_reader_switch, "active")
        bind_settings("replay", self.replay_switch, "active")
        bind_settings("rewind-duration", self.rewind_duration_adjustment, "value")
        bind_settings("forward-duration", self.forward_duration_adjustment, "value")
        bind_settings("sleep-timer-fadeout", self.sleep_timer_fadeout_switch, "enable-expansion")
        bind_settings("sleep-timer-fadeout-duration", self.fadeout_duration_adjustment, "value")
        bind_settings("prefer-external-cover", self.artwork_prefer_external_switch, "active")

    def _on_lock_ui_changed(self) -> None:
        self.storage_locations_view.set_sensitive(not self._view_model.lock_ui)

    def present(self, parent: Adw.ApplicationWindow) -> None:
        super().present(parent)

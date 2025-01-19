from __future__ import annotations

import inject
from gi.repository import Adw, Gio, GLib, Gtk

from cozy.control.time_format import min_to_human_readable, seconds_to_time
from cozy.view_model.sleep_timer_view_model import SleepTimerViewModel, SystemPowerAction


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/sleep_timer_dialog.ui")
class SleepTimer(Adw.Dialog):
    __gtype_name__ = "SleepTimer"

    _view_model = inject.attr(SleepTimerViewModel)

    list: Adw.PreferencesGroup = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()
    set_timer_button: Gtk.Button = Gtk.Template.Child()
    timer_state: Adw.StatusPage = Gtk.Template.Child()
    toolbarview: Adw.ToolbarView = Gtk.Template.Child()
    till_end_of_chapter_button_row: Adw.ButtonRow = Gtk.Template.Child()
    power_action_combo_row: Adw.ComboRow() = Gtk.Template.Child()

    def __init__(self, parent_button: Gtk.Button):
        super().__init__()
        self._parent_button = parent_button

        self.custom_adjustment = Gtk.Adjustment(lower=1, upper=300, value=20, step_increment=1)

        timer_action_group = Gio.SimpleActionGroup()
        self.insert_action_group("timer", timer_action_group)

        self.sleep_timer_action = Gio.SimpleAction(
            name="selected", state=GLib.Variant("n", 0), parameter_type=GLib.VariantType("n")
        )
        timer_action_group.add_action(self.sleep_timer_action)
        self.sleep_timer_action.connect("notify::state", self._on_timer_interval_selected)

        first_row = self._create_timer_selection_row(5)
        self.list.add(first_row)

        for duration in (15, 30, 60, -2):
            self.list.add(self._create_timer_selection_row(duration, first_row))

        self.spin_row = self._create_spin_timer_row(first_row)
        self.list.add(self.spin_row)
        self.custom_adjustment.connect("value-changed", self._update_custom_interval_text)
        self._update_custom_interval_text()

        self.power_action_list = [_("None"), _("Suspend"), _("Shutdown")]
        power_action_list_model = Gtk.StringList.new(self.power_action_list)
        self.power_action_combo_row.props.model = power_action_list_model

        self._connect_view_model()

    def _connect_view_model(self):
        self._view_model.bind_to("stop_after_chapter", self._on_stop_after_chapter_changed)
        self._view_model.bind_to("remaining_seconds", self._on_remaining_seconds_changed)
        self._view_model.bind_to("timer_enabled", self._on_timer_enabled_changed)

    def _add_radio_button_to_timer_row(
        self, row: Adw.ActionRow, action_target: int, group: Gtk.CheckButton | None
    ) -> None:
        radio = Gtk.CheckButton(
            css_classes=["selection-mode"],
            group=group,
            action_name="timer.selected",
            action_target=GLib.Variant("n", action_target),
            can_focus=False,
        )
        row.radio = radio
        row.set_activatable_widget(radio)
        row.add_prefix(radio)

    def _create_timer_selection_row(
        self, duration: int, group: Adw.ActionRow | None = None
    ) -> Adw.ActionRow:
        title = _("End of Chapter") if duration == -2 else min_to_human_readable(duration)
        row = Adw.ActionRow(title=title)
        self._add_radio_button_to_timer_row(row, duration, group.radio if group else None)

        return row

    def _create_spin_timer_row(self, group: Adw.ActionRow) -> Adw.SpinRow:
        spin_row = Adw.SpinRow(adjustment=self.custom_adjustment)
        spin_row.add_css_class("sleep-timer")
        self._add_radio_button_to_timer_row(spin_row, -1, group.radio)

        spin_button = spin_row.get_first_child().get_last_child().get_last_child()
        spin_button.set_halign(Gtk.Align.END)

        spin_row.connect("input", lambda x, y: spin_row.activate() or 0)

        return spin_row

    def _update_custom_interval_text(self, *_) -> None:
        self.spin_row.set_title(min_to_human_readable(self.custom_adjustment.get_value()))

    def _on_timer_interval_selected(self, action, _):
        value = action.get_state().unpack()
        if value != 0:
            self.set_timer_button.set_sensitive(True)

    def _on_remaining_seconds_changed(self):
        self.timer_state.set_title(seconds_to_time(self._view_model.remaining_seconds))

    def _on_stop_after_chapter_changed(self):
        self.till_end_of_chapter_button_row.set_visible(not self._view_model.stop_after_chapter)
        if self._view_model.stop_after_chapter:
            self.timer_state.set_title(_("Stopping After Current Chapter"))

    def _on_timer_enabled_changed(self):
        self.stack.set_visible_child_name(
            "running" if self._view_model.timer_enabled else "uninitiated"
        )
        self.toolbarview.set_reveal_bottom_bars(not self._view_model.timer_enabled)
        self._parent_button.set_icon_name(
            "bed-symbolic" if self._view_model.timer_enabled else "no-bed-symbolic"
        )

    def present(self, *_) -> None:
        super().present(inject.instance("MainWindow").window)

    @Gtk.Template.Callback()
    def close(self, *_):
        super().close()

    @Gtk.Template.Callback()
    def set_timer(self, *_):
        super().close()

        value = self.sleep_timer_action.get_state().unpack()
        if value == -1:
            self._view_model.remaining_seconds = self.custom_adjustment.get_value() * 60
        elif value == -2:
            self._view_model.stop_after_chapter = True
        else:
            self._view_model.remaining_seconds = value * 60

    @Gtk.Template.Callback()
    def plus_5_minutes(self, *_):
        if self._view_model.stop_after_chapter:
            self._view_model.remaining_seconds = self._view_model.get_remaining_from_chapter() + 300
        else:
            self._view_model.remaining_seconds += 300

    @Gtk.Template.Callback()
    def till_end_of_chapter(self, *_):
        self._view_model.stop_after_chapter = True

    @Gtk.Template.Callback()
    def cancel_timer(self, *_):
        super().close()
        self._view_model.remaining_seconds = 0
        self._view_model.stop_after_chapter = False

    @Gtk.Template.Callback()
    def on_power_action_selected(self, obj, _):
        selected_string = obj.props.selected_item.get_string()
        selected_string_index = self.power_action_list.index(selected_string)
        self._view_model.system_power_action = SystemPowerAction(selected_string_index)

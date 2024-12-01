from __future__ import annotations

import inject
from gi.repository import Adw, Gtk, GObject, GLib, Gio

from cozy.view_model.sleep_timer_view_model import SleepTimerViewModel, SystemPowerControl
from cozy.control.time_format import min_to_human_readable, seconds_to_time


class TimerRow(Adw.ActionRow):
    def __init__(self, group: TimerRow | None = None, target = 0):
        super().__init__(title=_("End of Chapter") if target == -2 else min_to_human_readable(target))
        self.radio = Gtk.CheckButton(
            css_classes=["selection-mode"],
            group=group.radio if group else None,
            action_name="timer.selected",
            action_target=GLib.Variant("n", target))
        self.set_activatable_widget(self.radio)
        self.add_prefix(self.radio)


@Gtk.Template.from_resource('/com/github/geigi/cozy/ui/timer_popover.ui')
class SleepTimer(Adw.Dialog):
    __gtype_name__ = "SleepTimer"

    _view_model = inject.attr(SleepTimerViewModel)

    list: Adw.PreferencesGroup = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()
    set_timer_button: Gtk.Button = Gtk.Template.Child()
    timer_state: Adw.StatusPage = Gtk.Template.Child()
    toolbarview: Adw.ToolbarView = Gtk.Template.Child()
    till_end_of_chapter_button_row: Adw.ButtonRow = Gtk.Template.Child()

    def __init__(self, parent_button: Gtk.Button):
        super().__init__()
        self.stack.set_visible_child_name("uninitiated")

        self._parent_button = parent_button

        demo_group = Gio.SimpleActionGroup()
        self.insert_action_group("timer", demo_group)

        self.sleep_timer_action = Gio.SimpleAction(
            name="selected",
            state=GLib.Variant("n", 0),
            parameter_type=GLib.VariantType("n"),
        )
        demo_group.add_action(self.sleep_timer_action)
        self.sleep_timer_action.connect("notify::state", self._timer_interval_selected)

        self.custom_adjustment = Gtk.Adjustment(lower=1, upper=1200, value=20, step_increment=1)

        min_1 = TimerRow(target=5)
        self.list.add(min_1)

        for i in (15, 30, 60, -2):
            self.list.add(TimerRow(min_1, i))

        self.spin_row = self._create_spin_timer_row(min_1)
        self._update_custom_interval_text()
        self.list.add(self.spin_row)

        self._connect_widgets()
        self._connect_view_model()

    @Gtk.Template.Callback()
    def close(self, *_):
        super().close()

    @Gtk.Template.Callback()
    def set_timer(self, *_):
        value = self.sleep_timer_action.get_state().unpack()
        if value == -1:
            self._view_model.remaining_seconds = self.custom_adjustment.get_value() * 60
        elif value == -2:
            self._view_model.stop_after_chapter = True
        else:
            self._view_model.remaining_seconds = value * 60

        super().close()

    @Gtk.Template.Callback()
    def plus_5_minutes(self, *_):
        self._view_model.remaining_seconds += 300
        super().close()

    @Gtk.Template.Callback()
    def till_end_of_chapter(self, *_):
        self._view_model.stop_after_chapter = True
        super().close()

    @Gtk.Template.Callback()
    def cancel_timer(self, *_):
        self._view_model.remaining_seconds = 0
        self._view_model.stop_after_chapter = False
        super().close()

    def _timer_interval_selected(self, action, _):
        value = action.get_state().unpack()
        if value != 0:
            self.set_timer_button.set_sensitive(True)

    def _connect_widgets(self):
        # self.timer_scale.connect("value-changed", self._on_timer_scale_changed)
        # self.chapter_switch.connect("state-set", self._on_chapter_switch_changed)
        ...

    def _connect_view_model(self):
        self._view_model.bind_to("stop_after_chapter", self._on_stop_after_chapter_changed)
        self._view_model.bind_to("remaining_seconds", self._on_remaining_seconds_changed)
        self._view_model.bind_to("timer_enabled", self._on_timer_enabled_changed)

    def _create_spin_timer_row(self, group: TimerRow | None = None):
        spin_row = Adw.SpinRow(adjustment=self.custom_adjustment)
        spin_row.add_css_class("sleep-timer")
        self.custom_adjustment.connect("value-changed", self._update_custom_interval_text)

        radio = Gtk.CheckButton(css_classes=["selection-mode"],
            group=group.radio if group else None,
            action_name="timer.selected",
            action_target=GLib.Variant("n", -1))
        spin_row.set_activatable_widget(radio)
        spin_row.add_prefix(radio)
        return spin_row

    def _update_custom_interval_text(self, *_) -> None:
        self.spin_row.set_title(min_to_human_readable(self.custom_adjustment.get_value()))

    def _on_remaining_seconds_changed(self):
        self.timer_state.set_title(seconds_to_time(self._view_model.remaining_seconds))

    def _on_stop_after_chapter_changed(self):
        self.till_end_of_chapter_button_row.set_visible(not self._view_model.stop_after_chapter)
        if self._view_model.stop_after_chapter:
            self.timer_state.set_title(_("Stopping After Current Chapter"))

    def _on_timer_enabled_changed(self):
        self.stack.set_visible_child_name("running" if self._view_model.timer_enabled else "uninitiated")
        self.toolbarview.set_reveal_bottom_bars(not self._view_model.timer_enabled)
        self._parent_button.set_icon_name("bed-symbolic" if self._view_model.timer_enabled else "no-bed-symbolic")

    def present(self, *_) -> None:
        super().present(inject.instance("MainWindow").window)


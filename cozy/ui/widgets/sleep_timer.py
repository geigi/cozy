import gi

from cozy.ext import inject
from cozy.view_model.sleep_timer_view_model import SleepTimerViewModel, SystemPowerControl

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/timer_popover.ui')
class SleepTimer(Gtk.Popover):
    __gtype_name__ = "SleepTimer"

    _view_model = inject.attr(SleepTimerViewModel)

    timer_scale: Gtk.Scale = Gtk.Template.Child()
    timer_label: Gtk.Label = Gtk.Template.Child()
    timer_grid: Gtk.Grid = Gtk.Template.Child()
    min_label: Gtk.Label = Gtk.Template.Child()
    chapter_switch: Gtk.Switch = Gtk.Template.Child()

    power_control_switch: Gtk.Switch = Gtk.Template.Child()
    power_control_options: Gtk.Box = Gtk.Template.Child()
    system_shutdown_radiob: Gtk.CheckButton = Gtk.Template.Child()
    system_suspend_radiob: Gtk.CheckButton = Gtk.Template.Child()

    def __init__(self, timer_image: Gtk.Image):
        super().__init__()

        self._timer_image: Gtk.Image = timer_image

        self._init_timer_scale()
        self._connect_widgets()

        self._connect_view_model()

        self._on_timer_scale_changed(self.timer_scale)

    def _connect_widgets(self):
        self.timer_scale.connect("value-changed", self._on_timer_scale_changed)
        self.chapter_switch.connect("state-set", self._on_chapter_switch_changed)
        self.power_control_switch.connect("state-set", self._on_power_options_switch_changed)
        self.system_suspend_radiob.connect("toggled", self._on_system_action_radio_button_changed)
        self.system_shutdown_radiob.connect("toggled", self._on_system_action_radio_button_changed)

    def _connect_view_model(self):
        self._view_model.bind_to("stop_after_chapter", self._on_stop_after_chapter_changed)
        self._view_model.bind_to("remaining_seconds", self._on_remaining_seconds_changed)
        self._view_model.bind_to("timer_enabled", self._on_timer_enabled_changed)

    def _init_timer_scale(self):
        for i in range(0, 121, 30):
            self.timer_scale.add_mark(i, Gtk.PositionType.RIGHT, None)

    def _on_timer_scale_changed(self, scale: Gtk.Scale):
        value = scale.get_value()

        if value > 0:
            self.timer_label.set_visible(True)
            self.min_label.set_text(_("min"))
            text = str(int(value))
            self.timer_label.set_text(text)
            self._view_model.remaining_seconds = value * 60
        else:
            self.min_label.set_text(_("Off"))
            self.timer_label.set_visible(False)
            self._view_model.remaining_seconds = 0

    def _on_chapter_switch_changed(self, _, state):
        self.timer_grid.set_sensitive(not state)
        self._view_model.stop_after_chapter = state

    def _on_remaining_seconds_changed(self):
        if self._view_model.remaining_seconds < 1:
            value = 0
        else:
            value = int((self._view_model.remaining_seconds / 60)) + 1

        self.timer_scale.set_value(value)

    def _on_power_options_switch_changed(self, _, state):
        self.power_control_options.set_sensitive(state)

        if not state:
            self._view_model.system_power_control = SystemPowerControl.OFF
        else:
            self._on_system_action_radio_button_changed(None)

    def _on_system_action_radio_button_changed(self, _):
        if self.system_suspend_radiob.get_active():
            self._view_model.system_power_control = SystemPowerControl.SUSPEND
        else:
            self._view_model.system_power_control = SystemPowerControl.SHUTDOWN

    def _on_stop_after_chapter_changed(self):
        self.chapter_switch.set_active(self._view_model.stop_after_chapter)

    def _on_timer_enabled_changed(self):
        if self._view_model.timer_enabled:
            icon = "bed-symbolic"
        else:
            icon = "no-bed-symbolic"

        self._timer_image.set_from_icon_name(icon)

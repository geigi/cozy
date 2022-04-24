import gi
from gi.repository import GObject, Gdk

from cozy.control.string_representation import seconds_to_str

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/seek_bar.ui')
class SeekBar(Gtk.Box):
    __gtype_name__ = "SeekBar"

    progress_scale: Gtk.Scale = Gtk.Template.Child()
    current_label: Gtk.Label = Gtk.Template.Child()
    remaining_label: Gtk.Label = Gtk.Template.Child()
    remaining_event_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._progress_scale_pressed = False

        self._progress_scale_gesture = Gtk.GestureClick()
        self._progress_scale_gesture.connect("pressed", self._on_progress_scale_press)
        self._progress_scale_gesture.connect("released", self._on_progress_scale_release)
        self.progress_scale.add_controller(self._progress_scale_gesture)

        self._progress_scale_key = Gtk.EventControllerKey()
        self._progress_scale_key.connect("key-pressed", self._on_progress_scale_press)
        self._progress_scale_key.connect("key-released", self._on_progress_scale_release)
        self.progress_scale.add_controller(self._progress_scale_key)

    @property
    def position(self) -> float:
        return self.progress_scale.get_value()

    @position.setter
    def position(self, new_value: float):
        if not self._progress_scale_pressed:
            self.progress_scale.set_value(new_value)

    @property
    def length(self) -> float:
        return self.progress_scale.get_adjustment().get_upper()

    @length.setter
    def length(self, new_value: float):
        self.progress_scale.set_range(0, new_value)
        self._on_progress_scale_changed(None)

    @property
    def sensitive(self) -> bool:
        return self.progress_scale.get_sensitive()

    @sensitive.setter
    def sensitive(self, new_value: bool):
        self.progress_scale.set_sensitive(new_value)

    @property
    def visible(self) -> bool:
        return self.progress_scale.get_visible()

    @visible.setter
    def visible(self, value: bool):
        self.current_label.set_visible(value)
        self.progress_scale.set_visible(value)
        self.remaining_event_box.set_visible(value)

    def _on_progress_scale_changed(self, _):
        position = int(self.progress_scale.get_value())
        total = self.progress_scale.get_adjustment().get_upper()

        remaining_secs: int = int(total - position)
        current_text = seconds_to_str(position, total)
        remaining_text = seconds_to_str(remaining_secs, total)
        self.current_label.set_markup("<span font_features='tnum'>" + current_text + "</span>")
        self.remaining_label.set_markup("<span font_features='tnum'>-" + remaining_text + "</span>")

    def _on_progress_scale_release(self, _, __):
        self._progress_scale_pressed = False
        value = self.progress_scale.get_value()
        self.emit("position-changed", value)

    def _on_progress_key_pressed(self, _, event):
        if event.keyval == Gdk.KEY_Up or event.keyval == Gdk.KEY_Left:
            self.position = max(self.position - 30, 0)
            self.emit("position-changed", self.position)
        elif event.keyval == Gdk.KEY_Down or event.keyval == Gdk.KEY_Right:
            max_value = self.progress_scale.get_adjustment().get_upper()
            self.position = min(self.position + 30, max_value)
            self.emit("position-changed", self.position)

    def _on_progress_scale_press(self, _, __):
        self._progress_scale_pressed = True

        return False


GObject.signal_new('position-changed', SeekBar, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))

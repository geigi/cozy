from gi.repository import Gdk, GObject, Gtk

from cozy.control.string_representation import seconds_to_str


@Gtk.Template.from_resource('/com/github/geigi/cozy/seek_bar.ui')
class SeekBar(Gtk.Box):
    __gtype_name__ = "SeekBar"

    progress_scale: Gtk.Scale = Gtk.Template.Child()
    current_label: Gtk.Label = Gtk.Template.Child()
    remaining_label: Gtk.Label = Gtk.Template.Child()
    remaining_event_box: Gtk.Box = Gtk.Template.Child()

    length: float

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.length: float = 0.0
        self._progress_scale_pressed = False

        self.progress_scale.connect("value-changed", self._on_progress_scale_changed)

        self._progress_scale_gesture = Gtk.GestureClick()
        self._progress_scale_gesture.connect("pressed", self._on_progress_scale_press)
        self._progress_scale_gesture.connect("end", self._on_progress_scale_release)
        self.progress_scale.add_controller(self._progress_scale_gesture)

        self._progress_scale_key = Gtk.EventControllerKey()
        self._progress_scale_key.connect("key-pressed", self._on_progress_key_pressed)
        self.progress_scale.add_controller(self._progress_scale_key)

    @property
    def position(self) -> float:
        return self.progress_scale.get_value()

    @position.setter
    def position(self, new_value: float):
        if not self._progress_scale_pressed:
            self.progress_scale.set_value(new_value)

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
        total = self.length

        remaining_secs: int = int(total - position)
        current_text = seconds_to_str(position, total)
        remaining_text = seconds_to_str(remaining_secs, total)
        self.current_label.set_markup("<span font_features='tnum'>" + current_text + "</span>")
        self.remaining_label.set_markup("<span font_features='tnum'>-" + remaining_text + "</span>")

    def _on_progress_scale_release(self, *_):
        self._progress_scale_pressed = False
        value = self.progress_scale.get_value()
        self.emit("position-changed", value)

    def _on_progress_key_pressed(self, _, event, *__):
        if event in {Gdk.KEY_Up, Gdk.KEY_Left}:
            self.position = max(self.position - 30, 0)
        elif event in {Gdk.KEY_Down, Gdk.KEY_Right}:
            self.position = min(self.position + 30, 100)

        self.emit("position-changed", self.position)

    def _on_progress_scale_press(self, *_):
        self._progress_scale_pressed = True
        return False


GObject.signal_new('position-changed', SeekBar, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))

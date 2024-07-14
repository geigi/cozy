from gi.repository import Gdk, GObject, Gtk

from cozy.control.string_representation import seconds_to_str


@Gtk.Template.from_resource('/com/github/geigi/cozy/ui/seek_bar.ui')
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

        # HACK: Using a GtkGestureClick here is not possible, as GtkRange's internal
        # gesture controller claims the button press event, and thus the released signal doesn't get emitted.
        # Therefore we get its internal GtkGestureClick, and add our handlers to that.
        # Hacky workaround from: https://gitlab.gnome.org/GNOME/gtk/-/issues/4939
        # Ideally GtkRange would forward these signals, so we wouldn't need this hack
        # TODO: Add these signals to Gtk and make a MR?
        for controller in self.progress_scale.observe_controllers():
            if isinstance(controller, Gtk.GestureClick):
                click_gesture = controller
                break

        click_gesture.set_button(0)  # Enable all mouse buttons
        click_gesture.connect("pressed", self._on_progress_scale_press)
        click_gesture.connect("released", self._on_progress_scale_release)

        keyboard_controller = Gtk.EventControllerKey()
        keyboard_controller.connect("key-pressed", self._on_progress_key_pressed)
        self.progress_scale.add_controller(keyboard_controller)

    @GObject.Signal(arg_types=(object,))
    def position_changed(self, *_): ...

    @GObject.Signal
    def rewind(self): ...

    @GObject.Signal
    def forward(self): ...

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
        total = self.length
        position = int(total * self.progress_scale.get_value() / 100)
        remaining_secs = int(total - position)

        self.current_label.set_text(seconds_to_str(position, total))
        self.remaining_label.set_text(seconds_to_str(remaining_secs, total))

    def _on_progress_scale_release(self, *_):
        self._progress_scale_pressed = False
        value = self.progress_scale.get_value()
        self.emit("position-changed", value)

    def _on_progress_key_pressed(self, _, event, *__):
        if event in {Gdk.KEY_Up, Gdk.KEY_Left}:
            self.emit("rewind")
        elif event in {Gdk.KEY_Down, Gdk.KEY_Right}:
            self.emit("forward")

    def _on_progress_scale_press(self, *_):
        self._progress_scale_pressed = True

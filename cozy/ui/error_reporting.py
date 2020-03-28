from gi.repository import Gtk


class ErrorReporting:
    def __init__(self, parent_window):
        self.builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/error_reporting.ui")
        self.window: Gtk.Window = self.builder.get_object("error_reporting_window")
        self.window.set_transient_for(parent_window)

        self.adjustment = self.builder.get_object("verbose_adjustment")
        self.scale: Gtk.Scale = self.builder.get_object("verbose_scale")
        self.info_stack: Gtk.Stack = self.builder.get_object("info_stack")

        self.__init_scale()
        self.__connect()

        self._update_verbose_text(self.adjustment)
        self.window.show()

    def __init_scale(self):
        for i in range(1, 5):
            self.scale.add_mark(i, Gtk.PositionType.RIGHT, None)
        self.scale.set_round_digits(0)

    def __connect(self):
        self.adjustment.connect("value-changed", self._update_verbose_text)

    def _update_verbose_text(self, adjustment: Gtk.Adjustment):
        value = adjustment.get_value()
        self.info_stack.set_visible_child_name(str(int(value)))

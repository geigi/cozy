import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/error_reporting.ui')
class ErrorReporting(Gtk.Box):
    __gtype_name__ = 'ErrorReporting'

    verbose_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    verbose_scale: Gtk.Scale = Gtk.Template.Child()
    info_stack: Gtk.Stack = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__init_scale()
        self.__connect()

        self._update_verbose_text(self.verbose_adjustment)

    def __init_scale(self):
        for i in range(1, 5):
            self.verbose_scale.add_mark(i, Gtk.PositionType.RIGHT, None)
        self.verbose_scale.set_round_digits(0)

    def __connect(self):
        self.verbose_adjustment.connect("value-changed", self._update_verbose_text)

    def _update_verbose_text(self, adjustment: Gtk.Adjustment):
        value = adjustment.get_value()
        self.info_stack.set_visible_child_name(str(int(value)))

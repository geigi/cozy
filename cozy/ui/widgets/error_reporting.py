from gettext import gettext as _

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

LEVELS = [
    _("Disabled"),
    _("Basic error reporting"),
    _("Detailed error reporting"),
    _("Detailed error reporting with import errors")
]

LEVEL_DESCRIPTION = [
    _("No error or crash reporting."),
    _("The following information will be sent in case of an error or crash:")
]

LEVEL_DETAILS = {
    0: [],
    1: [_("Which type of error occurred"),
        _("Line of code where an error occurred"),
        _("Cozy's version"), ],
    2: [_("Linux distribution"),
        _("Desktop environment")],
    3: [_("Media type of files that Cozy couldn't import")]
}


@Gtk.Template.from_resource('/com/github/geigi/cozy/error_reporting.ui')
class ErrorReporting(Gtk.Box):
    __gtype_name__ = 'ErrorReporting'

    level_label: Gtk.Label = Gtk.Template.Child()
    description_label: Gtk.Label = Gtk.Template.Child()
    details_label: Gtk.Label = Gtk.Template.Child()

    verbose_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    verbose_scale: Gtk.Scale = Gtk.Template.Child()

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
        value = int(adjustment.get_value()) - 1

        self.level_label.set_text(LEVELS[value])
        self._update_description(value)
        self._update_details(value)

    def _update_description(self, value):
        detail_index = min(value, 1)
        self.description_label.set_text(LEVEL_DESCRIPTION[detail_index])

    def _update_details(self, value):
        details = ""
        for i in range(value + 1):
            for line in LEVEL_DETAILS[i]:
                details += "• {}\n".format(line)
        self.details_label.set_text(details)

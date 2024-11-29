from gettext import gettext as _

import inject
from gi.repository import Gtk

from cozy.settings import ApplicationSettings

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


@Gtk.Template.from_resource('/com/github/geigi/cozy/ui/error_reporting.ui')
class ErrorReporting(Gtk.Box):
    __gtype_name__ = 'ErrorReporting'

    level_label: Gtk.Label = Gtk.Template.Child()
    description_label: Gtk.Label = Gtk.Template.Child()
    details_label: Gtk.Label = Gtk.Template.Child()
    header_box: Gtk.Box = Gtk.Template.Child()

    verbose_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    verbose_scale: Gtk.Scale = Gtk.Template.Child()

    app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__init_scale()
        self._load_report_level()
        self.__connect()

        self.app_settings.add_listener(self._on_app_setting_changed)

    def show_header(self, show: bool):
        self.header_box.set_visible(show)

    def _load_report_level(self):
        level = self.app_settings.report_level
        self.verbose_adjustment.set_value(level + 1)
        self._update_ui_texts(level)

    def __init_scale(self):
        for i in range(1, 5):
            self.verbose_scale.add_mark(i, Gtk.PositionType.RIGHT, None)
        self.verbose_scale.set_round_digits(0)

    def __connect(self):
        self.verbose_adjustment.connect("value-changed", self._adjustment_changed)

    def _adjustment_changed(self, adjustment: Gtk.Adjustment):
        level = int(adjustment.get_value()) - 1
        self.app_settings.report_level = level
        self._update_ui_texts(level)

    def _update_ui_texts(self, level: int):
        self.level_label.set_text(LEVELS[level])
        self._update_description(level)
        self._update_details(level)

    def _update_description(self, value):
        detail_index = min(value, 1)
        self.description_label.set_text(LEVEL_DESCRIPTION[detail_index])

    def _update_details(self, value):
        details = ""
        for i in range(value + 1):
            for line in LEVEL_DETAILS[i]:
                details += f"• {line}\n"
        self.details_label.set_text(details)

    def _on_app_setting_changed(self, event, _):
        if event == "report-level":
            self._load_report_level()


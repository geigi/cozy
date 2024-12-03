from itertools import chain

import inject
from gi.repository import Adw, Gtk

from cozy.settings import ApplicationSettings

LEVELS = [
    _("Disabled"),
    _("Basic error reporting"),
    _("Detailed error reporting"),
    _("Detailed, with media types"),
]

LEVEL_DESCRIPTION = [
    _("No error or crash reporting."),
    _("The following information will be sent in case of an error or crash:"),
]

LEVEL_DETAILS = [
    [],
    [
        _("Which type of error occurred"),
        _("Line of code where an error occurred"),
        _("Cozy's version"),
    ],
    [_("Linux distribution"), _("Desktop environment")],
    [_("Media type of files that Cozy couldn't import")],
]


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/error_reporting.ui")
class ErrorReporting(Gtk.Box):
    __gtype_name__ = "ErrorReporting"

    description: Adw.ActionRow = Gtk.Template.Child()
    detail_combo: Adw.ComboRow = Gtk.Template.Child()

    app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        levels_list = Gtk.StringList(strings=LEVELS)
        self.detail_combo.props.model = levels_list
        self.detail_combo.connect("notify::selected-item", self._level_selected)

        self._load_report_level()

        self.app_settings.add_listener(self._on_app_setting_changed)

    def _load_report_level(self):
        level = self.app_settings.report_level
        self._update_description(level)
        self.detail_combo.set_selected(level)

    def _level_selected(self, obj, param) -> None:
        selected = obj.get_property(param.name).get_string()
        index = LEVELS.index(selected)
        self.app_settings.report_level = index
        self._update_description(index)

    def _update_description(self, level: int):
        self.description.set_title(LEVEL_DESCRIPTION[min(level, 1)])
        details = "\n".join(["• " + i for i in chain(*LEVEL_DETAILS[: level + 1])])
        self.description.set_subtitle(details)

    def _on_app_setting_changed(self, event, _):
        if event == "report-level":
            self._load_report_level()

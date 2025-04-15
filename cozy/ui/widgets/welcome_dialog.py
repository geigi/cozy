import os.path
from pathlib import Path

import inject
from gi.repository import Adw, Gtk

from cozy.settings import ApplicationSettings
from cozy.ui.widgets.storages import ask_storage_location
from cozy.view_model.storages_view_model import StoragesViewModel


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/welcome_dialog.ui")
class WelcomeDialog(Adw.Dialog):
    __gtype_name__ = "WelcomeDialog"

    app_settings: ApplicationSettings = inject.attr(ApplicationSettings)
    _storages_view_model: StoragesViewModel = inject.attr(StoragesViewModel)

    carousel: Adw.Carousel = Gtk.Template.Child()
    welcome_page: Adw.StatusPage = Gtk.Template.Child()
    reporting_page: Gtk.Box = Gtk.Template.Child()
    locations_page: Adw.StatusPage = Gtk.Template.Child()
    create_directory_switch: Adw.SwitchRow = Gtk.Template.Child()
    chooser_button_label: Adw.ButtonContent = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self._path = None
        self._order = [self.welcome_page, self.reporting_page, self.locations_page]

    @Gtk.Template.Callback()
    def advance(self, *_):
        self.carousel.scroll_to(self._order[int(self.carousel.get_position()) + 1], True)

    @Gtk.Template.Callback()
    def deny_reporting(self, _):
        self.app_settings.report_level = 0
        self.advance()

    @Gtk.Template.Callback()
    def accept_reporting(self, _):
        self.advance()

    @Gtk.Template.Callback()
    def choose_directory(self, _):
        ask_storage_location(self._ask_storage_location_callback, None)

    def _ask_storage_location_callback(self, path):
        self._path = path
        self.chooser_button_label.set_label(os.path.basename(path))

    @Gtk.Template.Callback()
    def done(self, __chooser_button_label):
        self.close()
        self.app_settings.first_launch = False

        if self.create_directory_switch.props.active:
            audiobooks_dir = Path.home() / _("Audiobooks")
            audiobooks_dir.mkdir(exist_ok=True)
            self._storages_view_model.add_storage_location(str(audiobooks_dir), default=True)

            inject.instance("MainWindow")._set_audiobook_path(self._path, default=False)
        else:
            inject.instance("MainWindow")._set_audiobook_path(self._path)

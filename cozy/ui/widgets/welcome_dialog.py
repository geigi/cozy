import inject
from gi.repository import Adw, Gtk

from cozy.view_model.playback_speed_view_model import PlaybackSpeedViewModel
from cozy.ui.widgets.error_reporting import ErrorReporting
from cozy.settings import ApplicationSettings

from cozy.ui.widgets.storages import ask_storage_location


@Gtk.Template.from_resource('/com/github/geigi/cozy/ui/welcome_dialog.ui')
class WelcomeDialog(Adw.Dialog):
    __gtype_name__ = "WelcomeDialog"

    app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    carousel: Adw.Carousel = Gtk.Template.Child()
    welcome_page: Adw.StatusPage = Gtk.Template.Child()
    reporting_page: Gtk.Box = Gtk.Template.Child()
    locations_page: Adw.StatusPage = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.order = [self.welcome_page, self.reporting_page, self.locations_page]

    @Gtk.Template.Callback()
    def deny_reporting(self, _):
        self.advance()
        self.app_settings.report_level = 0

    @Gtk.Template.Callback()
    def accept_reporting(self, _):
        self.advance()

    @Gtk.Template.Callback()
    def done(self, _):
        self.close()

    @Gtk.Template.Callback()
    def choose_directory(self, _):
        ask_storage_location(inject.instance("MainWindow")._set_audiobook_path, None)

    def advance(self):
        self.carousel.scroll_to(self.order[int(self.carousel.get_position()) + 1], True)

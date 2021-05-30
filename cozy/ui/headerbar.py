import logging

import gi

from cozy.ext import inject
from cozy.view_model.headerbar_view_model import HeaderbarViewModel, HeaderBarState

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Handy
from gi.repository.Handy import HeaderBar

log = logging.getLogger("Headerbar")

COVER_SIZE = 45


@Gtk.Template.from_resource('/com/github/geigi/cozy/headerbar.ui')
class Headerbar(HeaderBar):
    __gtype_name__ = "Headerbar"

    search_button: Gtk.MenuButton = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()

    spinner: Gtk.Spinner = Gtk.Template.Child()

    back_button: Gtk.Button = Gtk.Template.Child()
    category_toolbar: Handy.ViewSwitcher = Gtk.Template.Child()

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._header_container: Gtk.Box = main_window_builder.get_object("header_container")
        self._header_container.add(self)

        self._sort_stack: Gtk.Stack = main_window_builder.get_object("sort_stack")
        self.category_toolbar.set_stack(self._sort_stack)

        self._headerbar_view_model: HeaderbarViewModel = inject.instance(HeaderbarViewModel)
        self._init_app_menu()
        self._connect_view_model()
        self._connect_widgets()

    def _connect_view_model(self):
        self._headerbar_view_model.bind_to("state", self._on_state_changed)

    def _connect_widgets(self):
        self.back_button.connect("clicked", self._back_clicked)

    def _init_app_menu(self):
        self.menu_builder = Gtk.Builder.new_from_resource("/com/github/geigi/cozy/titlebar_menu.ui")
        menu = self.menu_builder.get_object("titlebar_menu")
        self.menu_button.set_menu_model(menu)

    def _on_state_changed(self):
        if self._headerbar_view_model.state == HeaderBarState.PLAYING:
            spinner_visible = False
            self.spinner.stop()
        else:
            spinner_visible = True
            self.spinner.start()

        self.spinner.set_visible(spinner_visible)

    def _back_clicked(self, _):
        self._headerbar_view_model.navigate_back()

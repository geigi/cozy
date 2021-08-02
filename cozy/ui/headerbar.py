import logging

import gi

from cozy.ext import inject
from cozy.ui.widgets.progress_popover import ProgressPopover
from cozy.view_model.headerbar_view_model import HeaderbarViewModel, HeaderBarState

gi.require_version('Gtk', '3.0')
gi.require_version('Dazzle', '1.0')
from gi.repository import Gtk, Handy
from gi.repository.Handy import HeaderBar
from gi.repository.Dazzle import ProgressMenuButton

log = logging.getLogger("Headerbar")

COVER_SIZE = 45


@Gtk.Template.from_resource('/com/github/geigi/cozy/headerbar.ui')
class Headerbar(HeaderBar):
    __gtype_name__ = "Headerbar"

    search_button: Gtk.MenuButton = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()

    progress_menu_button: ProgressMenuButton = Gtk.Template.Child()

    back_button: Gtk.Button = Gtk.Template.Child()
    category_toolbar: Handy.ViewSwitcherTitle = Gtk.Template.Child()

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._library_mobile_view_switcher: Handy.ViewSwitcherBar = main_window_builder.get_object(
            "library_mobile_view_switcher")
        self._library_mobile_revealer: Gtk.Revealer = main_window_builder.get_object("library_mobile_revealer")
        self._header_container: Gtk.Box = main_window_builder.get_object("header_container")
        self._header_container.pack_start(self, False, True, 0)

        self._sort_stack: Gtk.Stack = main_window_builder.get_object("sort_stack")
        self.category_toolbar.set_stack(self._sort_stack)
        self._library_mobile_view_switcher.set_stack(self._sort_stack)

        self.progress_popover = ProgressPopover()
        self.progress_menu_button.set_popover(self.progress_popover)

        self._headerbar_view_model: HeaderbarViewModel = inject.instance(HeaderbarViewModel)
        self._init_app_menu()
        self._connect_view_model()
        self._connect_widgets()

    def _connect_view_model(self):
        self._headerbar_view_model.bind_to("state", self._on_state_changed)
        self._headerbar_view_model.bind_to("work_progress", self._on_work_progress_changed)
        self._headerbar_view_model.bind_to("work_message", self._on_work_message_changed)
        self._headerbar_view_model.bind_to("can_navigate_back", self._on_can_navigate_back_changed)
        self._headerbar_view_model.bind_to("show_library_filter", self._on_show_library_filter_changed)
        self._headerbar_view_model.bind_to("lock_ui", self._on_lock_ui_changed)

    def _connect_widgets(self):
        self.back_button.connect("clicked", self._back_clicked)
        self.category_toolbar.connect("notify::title-visible", self._on_title_visible_changed)

    def _init_app_menu(self):
        self.menu_builder = Gtk.Builder.new_from_resource("/com/github/geigi/cozy/titlebar_menu.ui")
        menu = self.menu_builder.get_object("titlebar_menu")
        self.menu_button.set_menu_model(menu)

    def _on_state_changed(self):
        if self._headerbar_view_model.state == HeaderBarState.PLAYING:
            progress_visible = False
            self.progress_menu_button.set_progress(0)
        else:
            progress_visible = True

        self.progress_menu_button.set_visible(progress_visible)

    def _on_work_progress_changed(self):
        progress = self._headerbar_view_model.work_progress
        self.progress_menu_button.set_progress(progress)
        self.progress_popover.set_progress(progress)

    def _on_work_message_changed(self):
        self.progress_popover.set_message(self._headerbar_view_model.work_message)

    def _on_can_navigate_back_changed(self):
        self.back_button.set_visible(self._headerbar_view_model.can_navigate_back)

    def _on_show_library_filter_changed(self):
        self.category_toolbar.set_visible(self._headerbar_view_model.show_library_filter)

    def _back_clicked(self, _):
        self._headerbar_view_model.navigate_back()

    def _on_title_visible_changed(self, widget, param):
        visible = widget.get_property(param.name)
        self._library_mobile_revealer.set_reveal_child(visible)

    def _on_lock_ui_changed(self):
        self.search_button.set_sensitive(not self._headerbar_view_model.lock_ui)

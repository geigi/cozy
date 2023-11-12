import logging

import gi

from cozy.ext import inject
from cozy.ui.widgets.progress_popover import ProgressPopover
from cozy.view_model.headerbar_view_model import HeaderbarViewModel, HeaderBarState

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Adw

log = logging.getLogger("Headerbar")

COVER_SIZE = 45


@Gtk.Template.from_resource('/com/github/geigi/cozy/headerbar.ui')
class Headerbar(Adw.Bin):
    __gtype_name__ = "Headerbar"

    headerbar: Adw.HeaderBar = Gtk.Template.Child()

    show_sidebar_button: Gtk.ToggleButton = Gtk.Template.Child()
    search_button: Gtk.MenuButton = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()

    progress_menu_button: Gtk.MenuButton = Gtk.Template.Child()

    category_toolbar: Adw.ViewSwitcherTitle = Gtk.Template.Child()

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._library_mobile_view_switcher: Adw.ViewSwitcherBar = main_window_builder.get_object(
            "library_mobile_view_switcher")
        self._header_container: Adw.ToolbarView = main_window_builder.get_object("header_container")
        self._header_container.add_top_bar(self)

        self._split_view: Adw.OverlaySplitView = main_window_builder.get_object("split_view")

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
        self._split_view.connect("notify::show-sidebar", self._on_sidebar_toggle)
        self.show_sidebar_button.connect("notify::active", self._on_sidebar_toggle)

    def _init_app_menu(self):
        self.menu_builder = Gtk.Builder.new_from_resource("/com/github/geigi/cozy/titlebar_menu.ui")
        menu = self.menu_builder.get_object("titlebar_menu")
        self.menu_button.set_menu_model(menu)

    def _on_sidebar_toggle(self, widget, param):
        show_sidebar = widget.get_property(param.name)

        if widget is self.show_sidebar_button:
            self._split_view.props.show_sidebar = show_sidebar
        elif widget is self._split_view:
            self.show_sidebar_button.props.active = show_sidebar

    def _on_state_changed(self):
        if self._headerbar_view_model.state == HeaderBarState.PLAYING:
            progress_visible = False
            #TODO Replace progress menu button
            #self.progress_menu_button.set_progress(0)
        else:
            progress_visible = True

        #self.progress_menu_button.set_visible(progress_visible)

    def _on_work_progress_changed(self):
        progress = self._headerbar_view_model.work_progress
        #self.progress_menu_button.set_progress(progress)
        self.progress_popover.set_progress(progress)

    def _on_work_message_changed(self):
        self.progress_popover.set_message(self._headerbar_view_model.work_message)

    def _on_can_navigate_back_changed(self):
        pass

    def _on_show_library_filter_changed(self):
        self.category_toolbar.set_visible(self._headerbar_view_model.show_library_filter)
        #self._reveal_mobile_library_filter(self.category_toolbar.get_title_visible())

    def _back_clicked(self, _):
        self._headerbar_view_model.navigate_back()

    def _on_title_visible_changed(self, widget, param):
        visible = widget.get_property(param.name)
        self._reveal_mobile_library_filter(visible)

    def _reveal_mobile_library_filter(self, reveal: bool):
        reveal_bar = reveal and self._headerbar_view_model.show_library_filter
        self._library_mobile_view_switcher.set_reveal(reveal_bar)

    def _on_lock_ui_changed(self):
        self.search_button.set_sensitive(not self._headerbar_view_model.lock_ui)

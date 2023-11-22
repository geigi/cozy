import logging

import gi

from cozy.ext import inject
from cozy.ui.widgets.progress_popover import ProgressPopover
from cozy.view_model.headerbar_view_model import HeaderbarViewModel, HeaderBarState

from gi.repository import Adw, Gtk

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
    progress_spinner: Gtk.Spinner = Gtk.Template.Child()

    view_switcher: Adw.ViewSwitcher = Gtk.Template.Child()

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self.header_container: Adw.ToolbarView = main_window_builder.get_object("header_container")
        self.header_container.add_top_bar(self)

        self.mobile_view_switcher: Adw.ViewSwitcherBar = main_window_builder.get_object("mobile_view_switcher")
        self.split_view: Adw.OverlaySplitView = main_window_builder.get_object("split_view")

        self.sort_stack: Adw.ViewStack = main_window_builder.get_object("sort_stack")
        self.view_switcher.set_stack(self.sort_stack)
        self.mobile_view_switcher.set_stack(self.sort_stack)

        self.progress_popover = ProgressPopover()
        self.progress_menu_button.set_popover(self.progress_popover)

        self._headerbar_view_model: HeaderbarViewModel = inject.instance(HeaderbarViewModel)
        self._connect_view_model()
        self._connect_widgets()

    def _connect_view_model(self):
        self._headerbar_view_model.bind_to("state", self._on_state_changed)
        self._headerbar_view_model.bind_to("work_progress", self._on_work_progress_changed)
        self._headerbar_view_model.bind_to("work_message", self._on_work_message_changed)
        self._headerbar_view_model.bind_to("lock_ui", self._on_lock_ui_changed)

    def _connect_widgets(self):
        self.split_view.connect("notify::show-sidebar", self._on_sidebar_toggle)
        self.show_sidebar_button.connect("notify::active", self._on_sidebar_toggle)
        self.mobile_view_switcher.connect("notify::reveal", self._on_mobile_view)
        self.sort_stack.connect("notify::visible-child", self._on_sort_stack_changed)

    def _on_sort_stack_changed(self, widget, _):
        page = widget.props.visible_child_name

        self.show_sidebar_button.set_visible(page != "recent")

    def _on_mobile_view(self, widget, _):
        if widget.props.reveal:
            self.headerbar.set_title_widget(Adw.WindowTitle(title="Cozy"))
        else:
            self.headerbar.set_title_widget(self.view_switcher)

    def _on_sidebar_toggle(self, widget, param):
        show_sidebar = widget.get_property(param.name)

        if widget is self.show_sidebar_button:
            self.split_view.set_show_sidebar(show_sidebar)
        elif widget is self.split_view:
            self.show_sidebar_button.set_active(show_sidebar)

    def _on_state_changed(self):
        if self._headerbar_view_model.state == HeaderBarState.PLAYING:
            self.progress_menu_button.set_visible(False)
            self.progress_popover.set_progress(0)
            self.progress_spinner.stop()
        else:
            self.progress_menu_button.set_visible(True)
            self.progress_spinner.start()

    def _on_work_progress_changed(self):
        self.progress_popover.set_progress(self._headerbar_view_model.work_progress)

    def _on_work_message_changed(self):
        self.progress_popover.set_message(self._headerbar_view_model.work_message)

    def _on_lock_ui_changed(self):
        self.search_button.set_sensitive(not self._headerbar_view_model.lock_ui)

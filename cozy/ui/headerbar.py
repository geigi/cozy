import logging

from gi.repository import Adw, GObject, Gtk

from cozy.ext import inject
from cozy.ui.widgets.progress_popover import ProgressPopover
from cozy.view_model.headerbar_view_model import HeaderBarState, HeaderbarViewModel

log = logging.getLogger("Headerbar")


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/headerbar.ui")
class Headerbar(Gtk.Box):
    __gtype_name__ = "Headerbar"

    headerbar: Adw.HeaderBar = Gtk.Template.Child()

    search_bar: Gtk.SearchBar = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()

    show_sidebar_button: Gtk.ToggleButton = Gtk.Template.Child()
    search_button: Gtk.MenuButton = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()

    progress_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    progress_spinner: Adw.Spinner = Gtk.Template.Child()

    view_switcher: Adw.ViewSwitcher = Gtk.Template.Child()

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self.header_container: Adw.ToolbarView = main_window_builder.get_object("header_container")
        self.header_container.add_top_bar(self)

        self.mobile_view_switcher: Adw.ViewSwitcherBar = main_window_builder.get_object(
            "mobile_view_switcher"
        )
        self.split_view: Adw.OverlaySplitView = main_window_builder.get_object("split_view")

        self.sort_stack: Adw.ViewStack = main_window_builder.get_object("sort_stack")
        self.view_switcher.set_stack(self.sort_stack)
        self.mobile_view_switcher.set_stack(self.sort_stack)

        self.progress_popover = ProgressPopover()
        self.progress_menu_button.set_popover(self.progress_popover)

        self.search_bar.connect_entry(self.search_entry)
        self.search_bar.set_key_capture_widget(self.header_container)

        self._headerbar_view_model: HeaderbarViewModel = inject.instance(HeaderbarViewModel)
        self._connect_view_model()
        self._connect_widgets()

        self._set_show_sidebar_button_visible()

    def _connect_view_model(self):
        self._headerbar_view_model.bind_to("state", self._on_state_changed)
        self._headerbar_view_model.bind_to("work_progress", self._on_work_progress_changed)
        self._headerbar_view_model.bind_to("work_message", self._on_work_message_changed)
        self._headerbar_view_model.bind_to("lock_ui", self._on_lock_ui_changed)

    def _connect_widgets(self):
        self.split_view.connect("notify::show-sidebar", self._on_sidebar_toggle)
        self.show_sidebar_button.connect("notify::active", self._on_sidebar_toggle)
        self.mobile_view_switcher.connect("notify::reveal", self._on_mobile_view)
        self.sort_stack.connect("notify::visible-child", self._set_show_sidebar_button_visible)

        self.mobile_view_switcher.bind_property(
            "reveal", self.split_view, "collapsed", GObject.BindingFlags.SYNC_CREATE
        )

    def _on_mobile(self) -> bool:
        return self.mobile_view_switcher.props.reveal

    def _set_show_sidebar_button_visible(self, *_):
        page = self.sort_stack.props.visible_child_name

        if not self._on_mobile():
            self.show_sidebar_button.set_visible(False)
            self.split_view.set_collapsed(False)
            self.split_view.set_show_sidebar(page != "recent")
            return

        if self.mobile_view_switcher.props.reveal:
            self.show_sidebar_button.set_visible(page != "recent")
        else:
            self.show_sidebar_button.set_visible(False)

        self.search_button.set_active(False)

    def _on_mobile_view(self, widget, _):
        if widget.props.reveal:
            self.headerbar.set_title_widget(Adw.WindowTitle(title="Cozy"))
        else:
            self.headerbar.set_title_widget(self.view_switcher)

        self._set_show_sidebar_button_visible()

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
        else:
            self.progress_menu_button.set_visible(True)

    def _on_work_progress_changed(self):
        self.progress_popover.set_progress(self._headerbar_view_model.work_progress)

    def _on_work_message_changed(self):
        self.progress_popover.set_message(self._headerbar_view_model.work_message)

    def _on_lock_ui_changed(self):
        self.search_button.set_sensitive(not self._headerbar_view_model.lock_ui)

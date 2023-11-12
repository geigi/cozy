from gi.repository import Gtk, Adw

from cozy.ext import inject
from cozy.view_model.app_view_model import AppViewModel
from cozy.view import View

LIBRARY = "main"
EMPTY_STATE = "no_media"
PREPARING_LIBRARY = "import"
BOOK_DETAIL = "book_overview"


class AppView:
    _view_model: AppViewModel = inject.attr(AppViewModel)

    def __init__(self, builder: Gtk.Builder):
        self._builder = builder

        self._get_ui_elements()
        self._connect_view_model()
        self._connect_ui_elements()

        self._update_view_model_view(None, None)

    def _get_ui_elements(self):
        self._main_stack: Gtk.Stack = self._builder.get_object("main_stack")
        self._navigation_view: Adw.Leaflet = self._builder.get_object("navigation_view")

    def _connect_ui_elements(self):
        self._main_stack.connect("notify::visible-child", self._update_view_model_view)
        self._navigation_view.connect("notify::visible-page", self._update_view_model_view)

    def _connect_view_model(self):
        self._view_model.bind_to("view", self._on_view_changed)

    def _on_view_changed(self):
        view = self._view_model.view

        if view == View.EMPTY_STATE:
            self._main_stack.set_visible_child_name(EMPTY_STATE)
        elif view == View.PREPARING_LIBRARY:
            self._main_stack.set_visible_child_name(PREPARING_LIBRARY)
        elif view == View.LIBRARY:
            self._main_stack.set_visible_child_name(LIBRARY)

    def _update_view_model_view(self, *_):
        page = self._main_stack.props.visible_child_name

        if page == LIBRARY:
            if self._navigation_view.props.visible_page == BOOK_DETAIL:
                self._view_model.view = View.BOOK_DETAIL
            else:
                self._view_model.view = View.LIBRARY
        elif page == EMPTY_STATE:
            self._view_model.view = View.EMPTY_STATE
        elif page == PREPARING_LIBRARY:
            self._view_model.view = View.PREPARING_LIBRARY


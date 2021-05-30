from typing import Optional

from gi.repository import Gtk, Handy
from gi.repository.Gtk import Builder

from cozy.ext import inject
from cozy.ui.book_element import BookElement
from cozy.ui.delete_book_view import DeleteBookView
from cozy.ui.widgets.filter_list_box import FilterListBox
from cozy.view_model.library_view_model import LibraryViewModel, LibraryViewMode, LibraryPage

READER_PAGE = "reader"
AUTHOR_PAGE = "author"
RECENT_PAGE = "recent"
MAIN_BOOK_PAGE = "main"
MAIN_NO_RECENT_PAGE = "nothing_here"
NO_MEDIA_PAGE = "no_media"


class LibraryView:
    _view_model: LibraryViewModel = inject.attr(LibraryViewModel)

    def __init__(self, builder: Builder):
        self._builder = builder
        self._connected_book_element: Optional[BookElement] = None

        self._get_ui_elements()
        self._connect_ui_elements()

        self._connect_view_model()

        self.populate_book_box()

        self._on_library_view_mode_changed()

    def _get_ui_elements(self):
        self._filter_stack: Gtk.Stack = self._builder.get_object("sort_stack")
        self._main_stack: Gtk.Stack = self._builder.get_object("main_stack")
        self._book_box: Gtk.FlowBox = self._builder.get_object("book_box")
        self._filter_stack_revealer: Gtk.Revealer = self._builder.get_object("sort_stack_revealer")
        self._toolbar_revealer: Gtk.Revealer = self._builder.get_object("toolbar_revealer")
        self._book_box: Gtk.FlowBox = self._builder.get_object("book_box")
        self._author_box: FilterListBox = self._builder.get_object("author_box")
        self._reader_box: FilterListBox = self._builder.get_object("reader_box")
        self._library_leaflet: Handy.Leaflet = self._builder.get_object("library_leaflet")

    def _connect_ui_elements(self):
        self._filter_stack.connect("notify::visible-child", self._on_sort_stack_changed)
        self._main_stack.connect("notify::visible-child", self._on_main_stack_changed)
        self._book_box.set_sort_func(self._view_model.display_book_sort)
        self._book_box.set_filter_func(self._view_model.display_book_filter)
        self._author_box.connect("row-selected", self._apply_selected_filter)
        self._reader_box.connect("row-selected", self._apply_selected_filter)

    def _connect_view_model(self):
        self._view_model.bind_to("library_view_mode", self._on_library_view_mode_changed)
        self._view_model.bind_to("library_page", self._on_library_page_changed)
        self._view_model.bind_to("authors", self.populate_author)
        self._view_model.bind_to("readers", self.populate_reader)
        self._view_model.bind_to("books", self.populate_book_box)
        self._view_model.bind_to("books-filter", self._book_box.invalidate_filter)
        self._view_model.bind_to("books-filter", self._book_box.invalidate_sort)
        self._view_model.bind_to("selected_filter", self._select_filter_row)
        self._view_model.bind_to("current_book_in_playback", self._current_book_in_playback)
        self._view_model.bind_to("playing", self._playing)

    def _on_sort_stack_changed(self, widget, _):
        page = widget.props.visible_child_name

        view_mode = None
        if page == RECENT_PAGE:
            view_mode = LibraryViewMode.CURRENT
        elif page == AUTHOR_PAGE:
            view_mode = LibraryViewMode.AUTHOR
        elif page == READER_PAGE:
            view_mode = LibraryViewMode.READER

        self._view_model.library_view_mode = view_mode

    def _on_main_stack_changed(self, widget, _):
        page = widget.props.visible_child_name

        if page != MAIN_BOOK_PAGE:
            self._view_model.library_page = LibraryPage.NONE

    def populate_book_box(self):
        self._book_box.remove_all_children()

        for book in self._view_model.books:
            book_element = BookElement(book)
            book_element.connect("play-pause-clicked", self._play_book_clicked)
            book_element.connect("open-book-overview", self._open_book_overview_clicked)
            book_element.connect("book-removed", self._on_book_removed)
            book_element.show_all()
            self._book_box.add(book_element)

    def populate_author(self):
        self._author_box.populate(self._view_model.authors)

    def populate_reader(self):
        self._reader_box.populate(self._view_model.readers)

    def _on_library_view_mode_changed(self):
        visible_child_name = None
        reveal_filter_box = True
        active_filter_box: Gtk.ListBox = None

        view_mode = self._view_model.library_view_mode
        main_view_page = MAIN_BOOK_PAGE

        if len(self._view_model.books) < 1:
            main_view_page = NO_MEDIA_PAGE
            visible_child_name = RECENT_PAGE
            reveal_filter_box = False
        elif view_mode == LibraryViewMode.CURRENT:
            visible_child_name = RECENT_PAGE
            reveal_filter_box = False
            if not self._view_model.is_any_book_in_progress:
                main_view_page = MAIN_NO_RECENT_PAGE
        elif view_mode == LibraryViewMode.AUTHOR:
            visible_child_name = AUTHOR_PAGE
            reveal_filter_box = True
            active_filter_box = self._author_box
        elif view_mode == LibraryViewMode.READER:
            visible_child_name = READER_PAGE
            reveal_filter_box = True
            active_filter_box = self._reader_box

        # https://stackoverflow.com/questions/22178524/gtk-named-stack-childs/22182843#22182843
        self._main_stack.props.visible_child_name = main_view_page
        self._filter_stack.set_visible_child_name(visible_child_name)
        self._filter_stack_revealer.set_reveal_child(reveal_filter_box)
        self._toolbar_revealer.set_reveal_child(True)
        self._toolbar_revealer.show_all()

        if active_filter_box:
            self._apply_selected_filter(active_filter_box, active_filter_box.get_selected_row())

        self._invalidate_filters()

    def _on_library_page_changed(self):
        page = self._view_model.library_page

        if page == LibraryPage.FILTER:
            self._library_leaflet.set_visible_child_name("filter")
        elif page == LibraryPage.BOOKS:
            self._library_leaflet.set_visible_child_name("books")

    def _invalidate_filters(self):
        self._book_box.invalidate_filter()
        self._book_box.invalidate_sort()

    def _apply_selected_filter(self, _, row):
        if not row:
            return

        self._view_model.selected_filter = row.data
        self._invalidate_filters()
        self._view_model.library_page = LibraryPage.BOOKS

    def _select_filter_row(self):
        if self._view_model.library_view_mode == LibraryViewMode.AUTHOR:
            self._author_box.select_row_with_content(self._view_model.selected_filter)
        elif self._view_model.library_view_mode == LibraryViewMode.READER:
            self._reader_box.select_row_with_content(self._view_model.selected_filter)

    def _play_book_clicked(self, _, book):
        self._view_model.play_book(book)

    def _open_book_overview_clicked(self, _, book):
        self._view_model.open_book_detail(book)
        self._view_model.library_page = LibraryPage.NONE
        return True

    def _on_book_removed(self, _, book):
        delete_from_library = True
        delete_files = False

        if self._view_model.book_files_exist(book):
            dialog = DeleteBookView()
            delete_from_library = delete_files = dialog.get_delete_book()
            dialog.destroy()

        if delete_files:
            self._view_model.delete_book_files(book)

        if delete_from_library:
            self._view_model.remove_book(book)

    def _current_book_in_playback(self):
        if self._connected_book_element:
            self._connected_book_element.set_playing(False)

        self._connected_book_element = next((book_element
                                             for book_element
                                             in self._book_box.get_children()
                                             if book_element.book == self._view_model.current_book_in_playback),
                                            None)

    def _playing(self):
        if self._connected_book_element:
            self._connected_book_element.set_playing(self._view_model.playing)

from typing import Optional

import inject
from gi.repository import Adw, Gtk

from cozy.ui.delete_book_view import DeleteBookView
from cozy.ui.widgets.book_element import BookElement
from cozy.ui.widgets.filter_list_box import FilterListBox
from cozy.view_model.library_view_model import LibraryViewMode, LibraryViewModel

READER_PAGE = "reader"
AUTHOR_PAGE = "author"
RECENT_PAGE = "recent"
MAIN_BOOK_PAGE = "main"
WELCOME_PAGE = "welcome"

NO_RECENT_PAGE = "no_recent"
BOOKS_PAGE = "books"


class LibraryView:
    _view_model: LibraryViewModel = inject.attr(LibraryViewModel)

    def __init__(self, builder: Gtk.Builder):
        self._builder = builder
        self._connected_book_element: Optional[BookElement] = None

        self._get_ui_elements()
        self._connect_ui_elements()

        self._connect_view_model()

        self.populate_book_box()
        self.populate_author()
        self.populate_reader()

        self._on_library_view_mode_changed()

    def _get_ui_elements(self):
        self._filter_stack: Gtk.Stack = self._builder.get_object("sort_stack")
        self._main_stack: Gtk.Stack = self._builder.get_object("main_stack")
        self._navigation_view: Adw.NavigationView = self._builder.get_object("navigation_view")
        self._split_view: Adw.OverlaySplitView = self._builder.get_object("split_view")
        self._book_box: Gtk.FlowBox = self._builder.get_object("book_box")
        self._filter_stack_revealer: Gtk.Revealer = self._builder.get_object("sort_stack_revealer")
        self._author_box: FilterListBox = self._builder.get_object("author_box")
        self._reader_box: FilterListBox = self._builder.get_object("reader_box")
        self._book_stack: Gtk.Stack = self._builder.get_object("book_stack")

    def _connect_ui_elements(self):
        self._filter_stack.connect("notify::visible-child", self._on_sort_stack_changed)
        self._book_box.set_sort_func(self._view_model.display_book_sort)
        self._book_box.set_filter_func(self._view_model.display_book_filter)

        # We need to connect to row-activated because it will be emitted when the user clicks on a row
        # which is already activated. This is important for the mobile view
        # row-selected is needed because when setting the row using select_row (e.g. when searching), the row-activated
        # signal doesn't emit.
        self._author_box.connect("row-activated", self._on_filter_row_activated)
        self._reader_box.connect("row-activated", self._on_filter_row_activated)
        self._author_box.connect("row-selected", self._on_filter_row_activated)
        self._reader_box.connect("row-selected", self._on_filter_row_activated)

    def _connect_view_model(self):
        self._view_model.bind_to("library_view_mode", self._on_library_view_mode_changed)
        self._view_model.bind_to("authors", self.populate_author)
        self._view_model.bind_to("readers", self.populate_reader)
        self._view_model.bind_to("books", self.populate_book_box)
        self._view_model.bind_to("books-filter", self._book_box.invalidate_filter)
        self._view_model.bind_to("books-filter", self._book_box.invalidate_sort)
        self._view_model.bind_to("selected_filter", self._select_filter_row)
        self._view_model.bind_to("current_book_in_playback", self._current_book_in_playback)
        self._view_model.bind_to("playing", self._playing)
        self._view_model.bind_to("book-progress", self._on_book_progress_changed)

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

    def populate_book_box(self):
        for child in self._book_box:
            self._book_box.remove(child)

        for book in self._view_model.books:
            book_element = BookElement(book)
            book_element.connect("play-pause-clicked", self._play_book_clicked)
            book_element.connect("open-book-overview", self._open_book_overview_clicked)
            book_element.connect("book-removed", self._on_book_removed)
            self._book_box.append(book_element)

    def populate_author(self):
        self._author_box.populate(self._view_model.authors)

    def populate_reader(self):
        self._reader_box.populate(self._view_model.readers)

    def _on_library_view_mode_changed(self):
        visible_child_name = None
        active_filter_box: Gtk.ListBox = None

        view_mode = self._view_model.library_view_mode
        main_view_page = MAIN_BOOK_PAGE
        books_view_page = BOOKS_PAGE

        if len(self._view_model.books) < 1:
            main_view_page = WELCOME_PAGE
            visible_child_name = RECENT_PAGE
        elif view_mode == LibraryViewMode.CURRENT:
            visible_child_name = RECENT_PAGE
            if not self._view_model.is_any_book_in_progress:
                books_view_page = NO_RECENT_PAGE
        elif view_mode == LibraryViewMode.AUTHOR:
            visible_child_name = AUTHOR_PAGE
            active_filter_box = self._author_box
        elif view_mode == LibraryViewMode.READER:
            visible_child_name = READER_PAGE
            active_filter_box = self._reader_box

        # https://stackoverflow.com/questions/22178524/gtk-named-stack-childs/22182843#22182843
        self._main_stack.props.visible_child_name = main_view_page
        self._filter_stack.set_visible_child_name(visible_child_name)
        self._book_stack.set_visible_child_name(books_view_page)
        self._navigation_view.pop_to_tag("main")

        if active_filter_box:
            self._apply_selected_filter(active_filter_box.get_selected_row())

        self._invalidate_filters()

    def _invalidate_filters(self):
        self._book_box.invalidate_filter()
        self._book_box.invalidate_sort()

    def _apply_selected_filter(self, row):
        if not row:
            return

        self._view_model.selected_filter = row.data
        self._invalidate_filters()

    def _on_filter_row_activated(self, _, row):
        self._apply_selected_filter(row)

        return True

    def _select_filter_row(self):
        if self._view_model.library_view_mode == LibraryViewMode.AUTHOR:
            self._author_box.select_row_with_content(self._view_model.selected_filter)
        elif self._view_model.library_view_mode == LibraryViewMode.READER:
            self._reader_box.select_row_with_content(self._view_model.selected_filter)

    def _play_book_clicked(self, _, book):
        self._view_model.play_book(book)

    def _open_book_overview_clicked(self, _, book):
        self._view_model.open_book_detail(book)

        return True

    def _on_book_removed(self, _, book):
        if self._view_model.book_files_exist(book):
            DeleteBookView(self._on_book_removed_clicked, book).present()

    def _on_book_removed_clicked(self, _, response, book):
        if response != "delete":
            return

        delete_from_library = True
        delete_files = True  # TODO: maybe an option to not delete the files

        if delete_files:
            self._view_model.delete_book_files(book)

        if delete_from_library:
            self._view_model.remove_book(book)

    def _current_book_in_playback(self):
        if self._connected_book_element:
            self._connected_book_element.set_playing(False)

        self._connected_book_element = None

        index = 0
        while book_element := self._book_box.get_child_at_index(index):
            if book_element.book == self._view_model.current_book_in_playback:
                self._connected_book_element = book_element
                break
            index += 1

    def _playing(self):
        if self._connected_book_element:
            self._connected_book_element.set_playing(self._view_model.playing)

    def _on_book_progress_changed(self):
        if not self._connected_book_element:
            return

        self._connected_book_element.update_progress()

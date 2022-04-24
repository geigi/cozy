import threading
from threading import Thread

from cozy.ext import inject
from cozy.ui.widgets.search_results import BookSearchResult, ArtistSearchResult

import gi

from cozy.view_model.search_view_model import SearchViewModel

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib


# TODO: There is a lot of app logic in this class that should be in the view model.
#  Ideally this class only retrieves lists of results from the view model and only handles displaying them.
class SearchView:
    view_model = inject.attr(SearchViewModel)

    search_thread = None
    search_thread_stop = None

    def __init__(self):
        self.builder = Gtk.Builder.new_from_resource("/com/github/geigi/cozy/search_popover.ui")

        self.popover = self.builder.get_object("search_popover")

        self.book_label = self.builder.get_object("book_label")
        self.track_label = self.builder.get_object("track_label")
        self.author_label = self.builder.get_object("author_label")
        self.reader_label = self.builder.get_object("reader_label")
        self.reader_box = self.builder.get_object("reader_result_box")
        self.author_box = self.builder.get_object("author_result_box")
        self.book_box = self.builder.get_object("book_result_box")
        self.track_box = self.builder.get_object("track_result_box")
        self.entry = self.builder.get_object("search_entry")
        self.scroller = self.builder.get_object("search_scroller")
        self.book_separator = self.builder.get_object("book_separator")
        self.author_separator = self.builder.get_object("author_separator")
        self.reader_separator = self.builder.get_object("reader_separator")
        self.stack = self.builder.get_object("search_stack")

        self.entry.connect("search-changed", self.__on_search_changed)

        if Gtk.get_minor_version() > 20:
            self.scroller.set_max_content_width(400)
            self.scroller.set_max_content_height(600)
            self.scroller.set_propagate_natural_height(True)
            self.scroller.set_propagate_natural_width(True)

        self.search_thread = Thread(target=self.search, name="SearchThread")
        self.search_thread_stop = threading.Event()

        self._connect_view_model()

    def _connect_view_model(self):
        self.view_model.bind_to("search_open", self._on_search_open_changed)

    def search(self, user_search: str):
        # we need the main context to call methods in the main thread after the search is finished
        main_context = GLib.MainContext.default()

        books = list({
            book
            for book
            in self.view_model.books
            if user_search.lower() in book.name.lower()
               or user_search.lower() in book.author.lower()
               or user_search.lower() in book.reader.lower()
        })
        books = sorted(books, key=lambda book: book.name.lower())
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_book_search_finished, books)

        authors = sorted({
            author
            for author
            in self.view_model.authors
            if user_search.lower() in author.lower()
        })
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_author_search_finished, authors)

        readers = sorted({
            reader
            for reader
            in self.view_model.readers
            if user_search.lower() in reader.lower()
        })
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_reader_search_finished, readers)

        if len(readers) < 1 and len(authors) < 1 and len(books) < 1:
            main_context.invoke_full(
                GLib.PRIORITY_DEFAULT, self.stack.set_visible_child_name, "nothing")

    def close(self, object=None):
        if Gtk.get_minor_version() < 22:
            self.popover.hide()
        else:
            self.popover.popdown()

    def __on_search_changed(self, sender):
        self.search_thread_stop.set()

        # we want to avoid flickering of the search box size
        # as we remove widgets and add them again
        # so we get the current search popup size and set it as
        # the preferred size until the search is finished
        # this helps only a bit, the widgets are still flickering
        self.popover.set_size_request(self.popover.get_allocated_width(),
                                      self.popover.get_allocated_height())

        # hide nothing found
        self.stack.set_visible_child_name("main")

        # First clear the boxes
        self.book_box.remove_all_children()
        self.author_box.remove_all_children()
        self.reader_box.remove_all_children()

        # Hide all the labels & separators
        self.book_label.set_visible(False)
        self.author_label.set_visible(False)
        self.reader_label.set_visible(False)
        self.book_separator.set_visible(False)
        self.author_separator.set_visible(False)
        self.reader_separator.set_visible(False)
        self.track_label.set_visible(False)

        user_search = self.entry.get_text()
        if user_search:
            if self.search_thread.is_alive():
                self.search_thread.join(timeout=0.2)
            self.search_thread_stop.clear()
            self.search_thread = Thread(
                target=self.search, args=(user_search,))
            self.search_thread.start()
        else:
            self.stack.set_visible_child_name("start")
            self.popover.set_size_request(-1, -1)

    def _on_search_open_changed(self):
        if self.view_model.search_open == False:
            self.close()

    def __on_book_search_finished(self, books):
        if len(books) > 0:
            self.stack.set_visible_child_name("main")
            self.book_label.set_visible(True)
            self.book_separator.set_visible(True)

            for book in books:
                if self.search_thread_stop.is_set():
                    return

                book_result = BookSearchResult(book, self.view_model.jump_to_book)
                self.book_box.add(book_result)

    def __on_author_search_finished(self, authors):
        if len(authors) > 0:
            self.stack.set_visible_child_name("main")
            self.author_label.set_visible(True)
            self.author_separator.set_visible(True)

            for author in authors:
                if self.search_thread_stop.is_set():
                    return

                author_result = ArtistSearchResult(self.view_model.jump_to_author, author, True)
                self.author_box.add(author_result)

    def __on_reader_search_finished(self, readers):
        if len(readers) > 0:
            self.stack.set_visible_child_name("main")
            self.reader_label.set_visible(True)
            self.reader_separator.set_visible(True)

            for reader in readers:
                if self.search_thread_stop.is_set():
                    return

                reader_result = ArtistSearchResult(self.view_model.jump_to_reader, reader, False)
                self.reader_box.add(reader_result)

        self.popover.set_size_request(-1, -1)

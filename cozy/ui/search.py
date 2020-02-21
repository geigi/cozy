import threading
from threading import Thread

from cozy.control.db import search_books, search_authors, search_readers
from cozy.ui.search_results import BookSearchResult, ArtistSearchResult
import cozy.tools as tools
import cozy.ui

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class Search:
    """
    This class contains all search logic.
    """
    search_thread = None
    search_thread_stop = None

    def __init__(self):
        self.ui = cozy.ui.main_view.CozyUI()
        self.builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/search_popover.ui")

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

    def get_popover(self):
        """
        Get the search popover
        :return: Search popover
        """
        return self.popover

    def search(self, user_search):
        """
        Perform a search with the current search entry
        """
        # we need the main context to call methods in the main thread after the search is finished
        main_context = GLib.MainContext.default()

        books = search_books(user_search)
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_book_search_finished, books)

        authors = search_authors(user_search)
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_author_search_finished, authors)

        readers = search_readers(user_search)
        if self.search_thread_stop.is_set():
            return
        main_context.invoke_full(
            GLib.PRIORITY_DEFAULT, self.__on_reader_search_finished, readers)

        if readers.count() < 1 and authors.count() < 1 and books.count() < 1:
            main_context.invoke_full(
                GLib.PRIORITY_DEFAULT, self.stack.set_visible_child_name, "nothing")

    def close(self, object=None):
        """
        Close the search popover specific to the used gtk version.
        """
        if Gtk.get_minor_version() < 22:
            self.popover.hide()
        else:
            self.popover.popdown()

    def __on_search_changed(self, sender):
        """
        Reset the search if running and start a new async search.
        """
        self.search_thread_stop.set()
        #self.throbber.set_visible(True)
        #self.throbber.start()

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
        tools.remove_all_children(self.book_box)
        tools.remove_all_children(self.author_box)
        tools.remove_all_children(self.reader_box)

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
                target=self.search, args=(user_search, ))
            self.search_thread.start()
        else:
            #self.throbber.stop()
            #self.throbber.set_visible(False)
            self.stack.set_visible_child_name("start")
            self.popover.set_size_request(-1, -1)

    def __on_book_search_finished(self, books):
        """
        This gets called after the book search is finished.
        It adds all the results to the gui.
        :param books: Result peewee query containing the books
        """
        if len(books) > 0:
            self.stack.set_visible_child_name("main")
            self.book_label.set_visible(True)
            self.book_separator.set_visible(True)

            for book in books:
                if self.search_thread_stop.is_set():
                    return
                self.book_box.add(BookSearchResult(
                    book, self.ui.jump_to_book, self.ui.window.get_scale_factor()))

    def __on_author_search_finished(self, authors):
        """
        This gets called after the author search is finished.
        It adds all the results to the gui.
        :param authors: Result peewee query containing the authors
        """
        if len(authors) > 0:
            self.stack.set_visible_child_name("main")
            self.author_label.set_visible(True)
            self.author_separator.set_visible(True)

            for author in authors:
                if self.search_thread_stop.is_set():
                    return
                self.author_box.add(ArtistSearchResult(self.ui.jump_to_author, author, True))

    def __on_reader_search_finished(self, readers):
        """
        This gets called after the reader search is finished.
        It adds all the results to the gui.
        It also resets the gui to a state before the search.
        :param readers: Result peewee query containing the readers
        """
        if len(readers) > 0:
            self.stack.set_visible_child_name("main")
            self.reader_label.set_visible(True)
            self.reader_separator.set_visible(True)

            for reader in readers:
                if self.search_thread_stop.is_set():
                    return
                self.reader_box.add(ArtistSearchResult(
                    self.ui.jump_to_reader, reader, False))

        # the reader search is the last that finishes
        # so we stop the throbber and reset the prefered height & width
        #self.throbber.stop()
        #self.throbber.set_visible(False)
        self.popover.set_size_request(-1, -1)
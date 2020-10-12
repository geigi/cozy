import logging

import gi

from cozy.db.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.model.book import Book
from cozy.report import reporter
from cozy.ui.disk_element import DiskElement
from cozy.ui.track_element import ChapterElement
from cozy.view_model.book_detail_view_model import BookDetailViewModel

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk

log = logging.getLogger("BookDetailView")


@Gtk.Template.from_resource('/com/github/geigi/cozy/book_detail.ui')
class BookDetailView(Gtk.Box):
    __gtype_name__ = 'BookDetail'

    book_label: Gtk.Label = Gtk.Template.Child()
    author_label: Gtk.Label = Gtk.Template.Child()
    last_played_label: Gtk.Label = Gtk.Template.Child()

    cover_image: Gtk.Image = Gtk.Template.Child()

    chapter_box: Gtk.Box = Gtk.Template.Child()

    _view_model: BookDetailViewModel = inject.attr(BookDetailViewModel)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._connect_view_model()

    def _connect_view_model(self):
        self.view_model.bind_to("book", self._on_book_changed)

    def _on_book_changed(self):
        if not self._view_model.book:
            msg = "ViewModel book was None."
            log.warning(msg)
            reporter.warning("BookDetailView", msg)
            return

        book = self._view_model.book

        self.published_label.set_visible(False)
        self.published_text.set_visible(False)

        self.book_label.set_text(book.name)
        self.author_label.set_text(book.author)
        self.last_played_label.set_text(self._view_model.last_played_text)

        self._set_cover_image(book)

    def _display_chapters(self, book: Book):
        disk_number = -1

        for chapter in book.chapters:
            if disk_number != chapter.disk and self._view_model.disk_count > 1:
                disc_element = DiskElement(chapter.disk)
                self.chapter_box.add(disc_element)

            track_element = ChapterElement(chapter)
            self.chapter_box.add(track_element)
            track_element.show_all()

            disk_number = chapter.disk

    def _set_cover_image(self, book):
        pixbuf = self._artwork_cache.get_cover_pixbuf(book.db_object, self.get_scale_factor(), 250)
        if pixbuf:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.get_scale_factor(), None)
            self.cover_image.set_from_surface(surface)
        else:
            self.cover_image.set_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.DIALOG)
            self.cover_image.props.pixel_size = 250

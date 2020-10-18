import logging

import gi

from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
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

    back_button: Gtk.Button = Gtk.Template.Child()

    book_label: Gtk.Label = Gtk.Template.Child()
    author_label: Gtk.Label = Gtk.Template.Child()
    last_played_label: Gtk.Label = Gtk.Template.Child()
    total_label: Gtk.Label = Gtk.Template.Child()

    remaining_label: Gtk.Label = Gtk.Template.Child()
    book_progress_bar: Gtk.ProgressBar = Gtk.Template.Child()

    published_label: Gtk.Label = Gtk.Template.Child()
    published_text: Gtk.Label = Gtk.Template.Child()

    download_box: Gtk.Box = Gtk.Template.Child()
    download_label: Gtk.Label = Gtk.Template.Child()
    download_image: Gtk.Image = Gtk.Template.Child()
    download_switch: Gtk.Switch = Gtk.Template.Child()

    cover_image: Gtk.Image = Gtk.Template.Child()

    chapter_box: Gtk.Box = Gtk.Template.Child()
    book_overview_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()

    _view_model: BookDetailViewModel = inject.attr(BookDetailViewModel)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._main_stack: Gtk.Stack = main_window_builder.get_object("main_stack")
        self._main_stack.add_named(self, "book_overview")

        if Gtk.get_minor_version() > 20:
            self.book_overview_scroller.props.propagate_natural_height = True

        self._connect_view_model()
        self._connect_widgets()

    def _connect_view_model(self):
        self._view_model.bind_to("book", self._on_book_changed)
        self._view_model.bind_to("is_book_available", self._view_model.open_library)
        self._view_model.bind_to("downloaded", self._set_book_download_status)

    def _connect_widgets(self):
        self.back_button.connect("clicked", self._back_button_clicked)

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
        self.total_label.set_text(self._view_model.total_text)

        self._set_cover_image(book)
        self._display_chapters(book)
        self._display_external_section()
        self._set_book_download_status()
        self._set_progress(book)

    def _display_chapters(self, book: Book):
        disk_number = -1

        self._clear_chapter_box()

        for chapter in book.chapters:
            if disk_number != chapter.disk and self._view_model.disk_count > 1:
                disk_number = chapter.disk
                self._add_disk(chapter)

            self._add_chapter(chapter)

            disk_number = chapter.disk

    def _display_external_section(self):
        external = self._view_model.is_book_external
        self.download_box.set_visible(external)
        self.download_switch.set_visible(external)

        if external:
            self.download_switch.set_active(self._view_model.is_book_external)

    def _add_disk(self, chapter: Chapter):
        disc_element = DiskElement(chapter.disk)
        self.chapter_box.add(disc_element)
        disc_element.show_all()

    def _add_chapter(self, chapter: Chapter):
        chapter_element = ChapterElement(chapter)
        self.chapter_box.add(chapter_element)
        chapter_element.show_all()

    def _clear_chapter_box(self):
        for child in self.chapter_box.get_children():
            if type(child) == ChapterElement:
                child.destroy_listeners()

        self.chapter_box.remove_all_children()

    def _set_progress(self, book: Book):
        self.remaining_label.set_text(self._view_model.remaining_text)
        self.book_progress_bar.set_fraction(self._view_model.progress_percent)

    def _set_cover_image(self, book: Book):
        pixbuf = self._artwork_cache.get_cover_pixbuf(book.db_object, self.get_scale_factor(), 250)
        if pixbuf:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.get_scale_factor(), None)
            self.cover_image.set_from_surface(surface)
        else:
            self.cover_image.set_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.DIALOG)
            self.cover_image.props.pixel_size = 250

    def _back_button_clicked(self, _):
        self._view_model.open_library()

    def _download_switch_changed(self, switch: Gtk.Switch, state: bool):
        self._view_model.download_book(state)

    def _set_book_download_status(self):
        if not self._view_model.is_book_external:
            return

        if self._view_model.book.downloaded:
            icon_name = "downloaded-symbolic"
            text = _("Downloaded")
        else:
            icon_name = "download-symbolic"
            text = _("Download")

        self.download_image.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        self.download_label.set_text(text)

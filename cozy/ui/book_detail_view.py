import logging
from typing import Optional

import gi

from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.report import reporter
from cozy.ui.disk_element import DiskElement
from cozy.ui.chapter_element import ChapterElement
from cozy.view_model.book_detail_view_model import BookDetailViewModel

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk

log = logging.getLogger("BookDetailView")


@Gtk.Template.from_resource('/com/github/geigi/cozy/book_detail.ui')
class BookDetailView(Gtk.EventBox):
    __gtype_name__ = 'BookDetail'

    back_button: Gtk.Button = Gtk.Template.Child()

    play_book_button: Gtk.Button = Gtk.Template.Child()
    play_img: Gtk.Image = Gtk.Template.Child()

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

    unavailable_box: Gtk.Box = Gtk.Template.Child()

    chapter_box: Gtk.Box = Gtk.Template.Child()
    book_overview_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()


    _view_model: BookDetailViewModel = inject.attr(BookDetailViewModel)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    _current_selected_chapter: Optional[ChapterElement] = None

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._main_stack: Gtk.Stack = main_window_builder.get_object("main_stack")
        self._toolbar_revealer: Gtk.Revealer = main_window_builder.get_object("toolbar_revealer")
        self._main_stack.add_named(self, "book_overview")

        if Gtk.get_minor_version() > 20:
            self.book_overview_scroller.props.propagate_natural_height = True

        self._connect_view_model()
        self._connect_widgets()
        self._add_mouse_button_accel()

    def _connect_view_model(self):
        self._view_model.bind_to("book", self._on_book_changed)
        self._view_model.bind_to("playing", self._on_play_changed)
        self._view_model.bind_to("is_book_available", self._on_book_available_changed)
        self._view_model.bind_to("downloaded", self._set_book_download_status)
        self._view_model.bind_to("current_chapter", self._on_current_chapter_changed)
        self._view_model.bind_to("last_played_text", self._on_last_played_text_changed)
        self._view_model.bind_to("remaining_text", self._on_times_changed)
        self._view_model.bind_to("progress_percent", self._on_times_changed)
        self._view_model.bind_to("total_text", self._on_times_changed)
        self._view_model.bind_to("playback_speed", self._on_times_changed)
        self._view_model.bind_to("lock_ui", self._on_lock_ui_changed)

    def _connect_widgets(self):
        self.back_button.connect("clicked", self._back_button_clicked)
        self.play_book_button.connect("clicked", self._play_book_clicked)
        self.download_switch.connect("state-set", self._download_switch_changed)

    def _add_mouse_button_accel(self):
        self.gesture = Gtk.GestureMultiPress(widget=self)
        self.gesture.set_button(0)
        self.gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture.connect('pressed', self._on_mouse_event)

    def _on_book_changed(self):
        if not self._view_model.book:
            msg = "ViewModel book was None."
            log.warning(msg)
            reporter.warning("BookDetailView", msg)
            return

        book = self._view_model.book
        self._current_selected_chapter = None

        self.published_label.set_visible(False)
        self.published_text.set_visible(False)

        self.book_label.set_text(book.name)
        self.author_label.set_text(book.author)
        self.last_played_label.set_text(self._view_model.last_played_text)
        self.total_label.set_text(self._view_model.total_text)

        self._set_cover_image(book)
        self._display_chapters(book)
        self._on_current_chapter_changed()
        self._display_external_section()
        self._set_book_download_status()
        self._set_progress()
        self._on_play_changed()
        self._on_book_available_changed()

        self._main_stack.set_visible_child_name("book_overview")
        self._toolbar_revealer.set_reveal_child(False)

    def _on_play_changed(self):
        playing = self._view_model.playing

        play_button_img = "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"
        self.play_img.set_from_icon_name(play_button_img, Gtk.IconSize.LARGE_TOOLBAR)

        if self._current_selected_chapter:
            self._current_selected_chapter.set_playing(playing)
        else:
            log.error("_current_selected_chapter is null. Skipping...")
            reporter.error("book_detail_view",
                           "_current_selected_chapter was NULL. No ply/pause chapter icon was changed")

    def _on_book_available_changed(self):
        info_visibility = not self._view_model.is_book_available
        self.unavailable_box.set_visible(info_visibility)

    def _on_current_chapter_changed(self):
        if self._current_selected_chapter:
            self._current_selected_chapter.deselect()

        current_chapter = self._view_model.current_chapter

        for child in self.chapter_box:
            if not isinstance(child, ChapterElement):
                continue

            if child.chapter == current_chapter:
                self._current_selected_chapter = child
                child.select()
                child.set_playing(self._view_model.playing)
                break

    def _on_last_played_text_changed(self):
        self.last_played_label.set_text(self._view_model.last_played_text)

    def _on_times_changed(self):
        self.total_label.set_text(self._view_model.total_text)
        self._set_progress()

    def _on_lock_ui_changed(self):
        lock = self._view_model.lock_ui
        self.download_switch.set_sensitive(not lock)

    def _display_chapters(self, book: Book):
        disk_number = -1

        self._clear_chapter_box()

        for chapter in book.chapters:
            if disk_number != chapter.disk and self._view_model.disk_count > 1:
                self._add_disk(chapter)

            self._add_chapter(chapter)

            disk_number = chapter.disk

    def _display_external_section(self):
        external = self._view_model.is_book_external
        self.download_box.set_visible(external)
        self.download_switch.set_visible(external)

        if external:
            self.download_switch.handler_block_by_func(self._download_switch_changed)
            self.download_switch.set_active(self._view_model.book.offline)
            self.download_switch.handler_unblock_by_func(self._download_switch_changed)

    def _add_disk(self, chapter: Chapter):
        disc_element = DiskElement(chapter.disk)
        self.chapter_box.add(disc_element)
        disc_element.show_all()

    def _add_chapter(self, chapter: Chapter):
        chapter_element = ChapterElement(chapter)
        chapter_element.connect("play-pause-clicked", self._play_chapter_clicked)
        self.chapter_box.add(chapter_element)
        chapter_element.show_all()

    def _clear_chapter_box(self):
        self.chapter_box.remove_all_children()

    def _set_progress(self):
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

    def _download_switch_changed(self, _, state: bool):
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

    def _play_chapter_clicked(self, _, chapter: Chapter):
        self._view_model.play_chapter(chapter)

    def _play_book_clicked(self, _):
        self._view_model.play_book()

    def _on_mouse_event(self, gesture: Gtk.GestureMultiPress, _, __, ___):
        btn = gesture.get_current_button()
        if btn == 8:
            self._view_model.open_library()
            return True

        return False

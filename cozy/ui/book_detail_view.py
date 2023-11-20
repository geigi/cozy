import logging
import time
from threading import Event, Thread
from typing import Optional, Callable

import gi

from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.report import reporter
from cozy.ui.chapter_element import ChapterElement
from cozy.ui.disk_element import DiskElement
from cozy.view_model.book_detail_view_model import BookDetailViewModel

from gi.repository import Adw, GLib, Gtk

log = logging.getLogger("BookDetailView")


ALBUM_ART_SIZE = 256


@Gtk.Template.from_resource('/com/github/geigi/cozy/book_detail.ui')
class BookDetailView(Gtk.Box):
    __gtype_name__ = 'BookDetail'

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

    album_art: Gtk.Picture = Gtk.Template.Child()
    album_art_container: Gtk.Box = Gtk.Template.Child()

    unavailable_box: Gtk.Box = Gtk.Template.Child()

    chapters_stack: Gtk.Stack = Gtk.Template.Child()
    chapter_box: Gtk.Box = Gtk.Template.Child()
    book_overview_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()

    main_flow_box: Gtk.FlowBox = Gtk.Template.Child()

    _view_model: BookDetailViewModel = inject.attr(BookDetailViewModel)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    _current_selected_chapter: Optional[ChapterElement] = None

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._navigation_view: Adw.NavigationView = main_window_builder.get_object("navigation_view")
        self._book_details_container: Adw.ToolbarView = main_window_builder.get_object("book_details_container")
        self._book_details_container.set_content(self)

        headerbar = Adw.HeaderBar()
        self.header_title = Adw.WindowTitle()
        headerbar.set_title_widget(self.header_title)
        self._book_details_container.add_top_bar(headerbar)

        self.book_overview_scroller.props.propagate_natural_height = True

        self._chapters_event: Event = Event()
        self._chapters_thread: Thread = None
        self._prepare_chapters_job()

        self._connect_view_model()
        self._connect_widgets()

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
        self._view_model.bind_to("open", self._on_open)

    def _connect_widgets(self):
        self.play_book_button.connect("clicked", self._play_book_clicked)
        self.download_switch.connect("state-set", self._download_switch_changed)
        # TODO: Use property notification for GtkWindow:default-width and GtkWindow:default-height
        #self.main_flow_box.connect("size-allocate", self._main_flow_box_size_changed)

    def _on_book_changed(self):
        if not self._view_model.book:
            msg = "ViewModel book was None."
            log.warning(msg)
            reporter.warning("BookDetailView", msg)
            return

        self._chapters_event.clear()

        book = self._view_model.book

        self.chapters_stack.set_visible_child_name("chapters_loader")
        self.book_overview_scroller.set_visible(False)
        self._run_display_chapters_job(book)

        self._current_selected_chapter = None

        self.published_label.set_visible(False)
        self.published_text.set_visible(False)
        self.total_label.set_visible(False)
        self.unavailable_box.set_visible(False)

        self.book_label.set_text(book.name)
        self.author_label.set_text(book.author)
        self.header_title.set_title(book.name)
        self.header_title.set_subtitle(book.author)

        self.last_played_label.set_text(self._view_model.last_played_text)

        self._set_cover_image(book)

        self._display_external_section()
        self._set_progress()

    def _on_open(self):
        if self._navigation_view.props.visible_page.props.tag == "book_overview":
            self._navigation_view.pop_to_tag("book_overview")
        else:
            self._navigation_view.push_by_tag("book_overview")

    def _on_play_changed(self):
        playing = self._view_model.playing

        play_button_img = "pause-symbolic" if playing else "play-symbolic"
        self.play_img.set_from_icon_name(play_button_img)

        if self._current_selected_chapter:
            self._current_selected_chapter.set_playing(playing)
        else:
            log.error("_current_selected_chapter is null. Skipping...")
            reporter.error("book_detail_view",
                           "_current_selected_chapter was NULL. No play/pause chapter icon was changed")

    def _on_book_available_changed(self):
        info_visibility = not self._view_model.is_book_available
        self.unavailable_box.set_visible(info_visibility)

    def _on_current_chapter_changed(self):
        if self._current_selected_chapter:
            self._current_selected_chapter.deselect()
            self._current_selected_chapter.set_playing(False)

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

    def _run_display_chapters_job(self, book):
        self._chapters_event.clear()
        # The job might be running on another thread. Attempt to cancel it first, wait a while and trigger the new one.
        self._interrupt_chapters_jobs()
        time.sleep(0.05)
        # This is done on a the UI thread to prevent chapters from the previous book flashing before the new chapters
        # are ready
        self._schedule_chapters_clearing()
        self._prepare_chapters_job()
        self._chapters_thread: Thread = Thread(target=self._schedule_chapters_rendering,
                                               args=[book, self._on_chapters_displayed])
        self._chapters_thread.start()

    def _schedule_chapters_rendering(self, book: Book, callback: Callable):
        disk_number = -1
        multiple_disks = self._view_model.disk_count > 1

        for chapter in book.chapters:
            if self._chapters_job_locked:
                self._schedule_chapters_clearing()
                return

            if multiple_disks and disk_number != chapter.disk:
                GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, self._add_disk, book.id, chapter)

            GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, self._add_chapter, book.id, chapter)

            disk_number = chapter.disk

            # TODO We need a timeout value
            self._chapters_event.wait()
            self._chapters_event.clear()

        GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, callback)

    def _on_chapters_displayed(self):
        self.total_label.set_text(self._view_model.total_text)
        self.total_label.set_visible(True)
        self._set_book_download_status()

        self._on_current_chapter_changed()
        self._on_play_changed()
        self._on_book_available_changed()

        self.book_overview_scroller.set_visible(True)
        self.chapters_stack.set_visible_child_name("chapters_wrapper")

    def _display_external_section(self):
        external = self._view_model.is_book_external
        self.download_box.set_visible(external)
        self.download_switch.set_visible(external)

        if external:
            self.download_switch.handler_block_by_func(self._download_switch_changed)
            self.download_switch.set_active(self._view_model.book.offline)
            self.download_switch.handler_unblock_by_func(self._download_switch_changed)

    def _add_disk(self, book_id: int, chapter: Chapter):
        if book_id != self._view_model.book.id:
            return

        disc_element = DiskElement(chapter.disk)
        self.chapter_box.append(disc_element)
        self._chapters_event.set()

    def _add_chapter(self, book_id: int, chapter: Chapter):
        if book_id != self._view_model.book.id:
            return

        chapter_element = ChapterElement(chapter)
        chapter_element.connect("play-pause-clicked", self._play_chapter_clicked)
        self.chapter_box.append(chapter_element)
        self._chapters_event.set()

    def _schedule_chapters_clearing(self):
        GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, self.chapter_box.remove_all_children)

    def _set_progress(self):
        self.remaining_label.set_text(self._view_model.remaining_text)
        self.book_progress_bar.set_fraction(self._view_model.progress_percent)

    def _set_cover_image(self, book: Book):
        paintable = self._artwork_cache.get_cover_paintable(book, self.get_scale_factor(), ALBUM_ART_SIZE)
        if paintable:
            self.album_art_container.set_visible(True)
            self.album_art.set_paintable(paintable)
            self.album_art.set_overflow(True)
        else:
            self.album_art_container.set_visible(False)

    def _interrupt_chapters_jobs(self):
        self._chapters_job_locked = True

        try:
            self._chapters_thread.join(timeout=0.2)
        except AttributeError as e:
            pass

    def _prepare_chapters_job(self):
        self._chapters_job_locked: bool = False

    def _download_switch_changed(self, _, state: bool):
        self._view_model.download_book(state)

    def _main_flow_box_size_changed(self, _, __):
        if self._is_chapter_box_wrapped():
            vertical_scroll_policy = Gtk.PolicyType.NEVER
        else:
            vertical_scroll_policy = Gtk.PolicyType.ALWAYS

        self.book_overview_scroller.set_policy(Gtk.PolicyType.NEVER, vertical_scroll_policy)

    def _is_chapter_box_wrapped(self):
        x, _ = self.book_overview_scroller.translate_coordinates(self.main_flow_box, 0, 0)

        return x < 100

    def _set_book_download_status(self):
        if not self._view_model.is_book_external:
            return

        if self._view_model.book.downloaded:
            icon_name = "downloaded-symbolic"
            text = _("Downloaded")
        else:
            icon_name = "download-symbolic"
            text = _("Download")

        self.download_image.set_from_icon_name(icon_name)
        self.download_label.set_text(text)

    def _play_chapter_clicked(self, _, chapter: Chapter):
        self._view_model.play_chapter(chapter)

    def _play_book_clicked(self, _):
        self._view_model.play_book()


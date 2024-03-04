import logging
import time
from threading import Event, Thread
from typing import Callable, Final

from gi.repository import Adw, GLib, Gtk

from cozy.control.artwork_cache import ArtworkCache
from cozy.ext import inject
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.report import reporter
from cozy.ui.chapter_element import ChapterElement
from cozy.view_model.book_detail_view_model import BookDetailViewModel

log = logging.getLogger("BookDetailView")

ALBUM_ART_SIZE: Final[int] = 256


def call_in_main_thread(*args) -> None:
    # TODO: move this elsewhere, it might come useful
    GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, *args)


class ChaptersListBox(Adw.PreferencesGroup):
    def __init__(self, title: str):
        super().__init__()
        self.set_title(title)

    def add_chapter(self, chapter: Chapter, callback: Callable[[None], None]):
        chapter_element = ChapterElement(chapter)
        chapter_element.connect("play-pause-clicked", callback)
        self.add(chapter_element)
        return chapter_element


@Gtk.Template.from_resource("/com/github/geigi/cozy/book_detail.ui")
class BookDetailView(Adw.BreakpointBin):
    __gtype_name__ = "BookDetail"

    play_button: Gtk.Button = Gtk.Template.Child()
    play_icon: Adw.ButtonContent = Gtk.Template.Child()

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

    unavailable_badge: Gtk.Box = Gtk.Template.Child()

    chapters_stack: Gtk.Stack = Gtk.Template.Child()
    chapter_list_container: Gtk.Box = Gtk.Template.Child()

    _view_model: BookDetailViewModel = inject.attr(BookDetailViewModel)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    _current_selected_chapter: ChapterElement | None = None

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._navigation_view: Adw.NavigationView = main_window_builder.get_object(
            "navigation_view"
        )
        self._book_details_container: Adw.ToolbarView = main_window_builder.get_object(
            "book_details_container"
        )
        self._book_details_container.set_content(self)

        self._book_details_container.add_top_bar(Adw.HeaderBar(show_title=False))

        self._chapters_event = Event()
        self._chapters_thread: Thread | None = None
        self._chapters_job_locked = False

        self._chapter_listboxes: list[ChaptersListBox] = []
        self._chapter_elements: list[ChapterElement] = []

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
        self.play_button.connect("clicked", self._play_book_clicked)
        self.download_switch.connect("state-set", self._download_switch_changed)

    def _on_book_changed(self):
        book = self._view_model.book

        if not book:
            message = "ViewModel book was None."
            log.warning(message)
            reporter.warning("BookDetailView", message)
            return

        self._chapters_event.clear()

        self.chapters_stack.set_visible_child_name("chapters_loader")
        self._display_chapters(book)

        self._current_selected_chapter = None

        self.published_label.set_visible(False)
        self.published_text.set_visible(False)
        self.total_label.set_visible(False)
        self.unavailable_badge.set_visible(False)

        self.book_label.set_text(book.name)
        self.author_label.set_text(book.author)

        self.last_played_label.set_text(self._view_model.last_played_text)

        self._set_cover_image(book)
        self._set_progress()
        self._display_external_section()

    def _on_open(self):
        if self._navigation_view.props.visible_page.props.tag == "book_overview":
            self._navigation_view.pop_to_tag("book_overview")
        else:
            self._navigation_view.push_by_tag("book_overview")

    def _on_play_changed(self):
        playing = self._view_model.playing

        if playing:
            self.play_icon.set_icon_name("media-playback-pause-symbolic")
            self.play_icon.set_label(_("Pause"))
        else:
            self.play_icon.set_icon_name("media-playback-start-symbolic")
            if not self._view_model.progress_percent:
                self.play_icon.set_label(_("Start"))
            else:
                self.play_icon.set_label(_("Resume"))

        if self._current_selected_chapter:
            self._current_selected_chapter.set_playing(playing)
        else:
            log.error("_current_selected_chapter is null. Skipping...")
            reporter.error(
                "book_detail_view",
                "_current_selected_chapter was NULL. No play/pause chapter icon was changed",
            )

    def _on_book_available_changed(self):
        self.unavailable_badge.set_visible(not self._view_model.is_book_available)

    def _on_current_chapter_changed(self):
        if self._current_selected_chapter:
            self._current_selected_chapter.deselect()
            self._current_selected_chapter.set_playing(False)

        current_chapter = self._view_model.current_chapter

        for child in self._chapter_elements:
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
        self.download_switch.set_sensitive(not self._view_model.lock_ui)

    def _on_chapters_displayed(self):
        self.total_label.set_text(self._view_model.total_text)
        self.total_label.set_visible(True)
        self._set_book_download_status()

        self._on_current_chapter_changed()
        self._on_play_changed()
        self._on_book_available_changed()

        self.chapters_stack.set_visible_child_name("chapters_wrapper")

    def _display_chapters(self, book):
        self._chapters_event.clear()

        # The job might be running on another thread. Attempt to cancel it first, wait a while and trigger the new one.
        self._interrupt_chapters_jobs()
        time.sleep(0.05)

        # This is done on a the UI thread to prevent chapters from the previous
        # book flashing before the new chapters are ready
        self._clear_chapters()
        self._chapters_job_locked = False
        self._chapters_thread = Thread(
            target=self._render_chapters, args=[book, self._on_chapters_displayed]
        )
        self._chapters_thread.start()

    def _clear_chapters(self) -> None:
        for listbox in self._chapter_listboxes:
            call_in_main_thread(self.chapter_list_container.remove, listbox)

        self._chapter_elements.clear()
        self._chapter_listboxes.clear()

    def _render_chapters(self, book: Book, callback: Callable) -> None:
        if book.id != self._view_model.book.id:
            return

        multiple_disks = self._view_model.disk_count > 1
        disk_number = -1

        if not multiple_disks:
            call_in_main_thread(self._add_section, _("Chapters"))

        for chapter in book.chapters:
            if self._chapters_job_locked:
                # Rendering was cancelled
                return self._clear_chapters()

            if multiple_disks and disk_number != chapter.disk:
                disk_number = chapter.disk
                section_title = _("Disc {disk_number}").format(disk_number=disk_number)
                call_in_main_thread(self._add_section, section_title)

            call_in_main_thread(self._add_chapter, chapter)

            # TODO We need a timeout value
            # Wait until the chapter is displayed
            self._chapters_event.wait()
            self._chapters_event.clear()

        call_in_main_thread(callback)

    def _add_section(self, title: str) -> ChaptersListBox:
        listbox = ChaptersListBox(title)
        self.chapter_list_container.append(listbox)
        self._chapter_listboxes.append(listbox)

    def _add_chapter(self, chapter: Chapter):
        current_listbox = self._chapter_listboxes[-1]
        element = current_listbox.add_chapter(chapter, self._play_chapter_clicked)
        self._chapter_elements.append(element)
        self._chapters_event.set()

    def _display_external_section(self):
        external = self._view_model.is_book_external
        self.download_box.set_visible(external)
        self.download_switch.set_visible(external)

        if external:
            self.download_switch.handler_block_by_func(self._download_switch_changed)
            self.download_switch.set_active(self._view_model.book.offline)
            self.download_switch.handler_unblock_by_func(self._download_switch_changed)

    def _set_progress(self):
        self.remaining_label.set_text(self._view_model.remaining_text)
        self.book_progress_bar.set_fraction(self._view_model.progress_percent)

    def _set_cover_image(self, book: Book):
        self.album_art_container.set_visible(False)

        paintable = self._artwork_cache.get_cover_paintable(
            book, self.get_scale_factor(), ALBUM_ART_SIZE
        )

        if paintable:
            self.album_art_container.set_visible(True)
            self.album_art.set_paintable(paintable)
            self.album_art.set_overflow(True)

    def _interrupt_chapters_jobs(self):
        self._chapters_job_locked = True

        if self._chapters_thread:
            self._chapters_thread.join(timeout=0.2)

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

    def _download_switch_changed(self, _, state: bool):
        self._view_model.download_book(state)
        self._set_book_download_status()

    def _play_chapter_clicked(self, _, chapter: Chapter):
        self._view_model.play_chapter(chapter)

    def _play_book_clicked(self, _):
        self._view_model.play_book()

import logging
import time
from math import pi as PI
from threading import Event, Thread
from typing import Callable, Final

import cairo
import inject
from gi.repository import Adw, Gio, GLib, GObject, Graphene, Gtk

from cozy.control.artwork_cache import ArtworkCache
from cozy.model.book import Book
from cozy.model.chapter import Chapter
from cozy.report import reporter
from cozy.ui.chapter_element import ChapterElement
from cozy.ui.toaster import ToastNotifier
from cozy.view_model.book_detail_view_model import BookDetailViewModel

log = logging.getLogger(__name__)

ALBUM_ART_SIZE: Final[int] = 256
PROGRESS_RING_LINE_WIDTH: Final[int] = 5


def call_in_main_thread(*args) -> None:
    # TODO: move this elsewhere, it might come useful
    GLib.MainContext.default().invoke_full(GLib.PRIORITY_DEFAULT_IDLE, *args)


class ProgressRing(Gtk.Widget):
    __gtype_name__ = "ProgressRing"

    progress = GObject.Property(type=float, default=0.0)

    def __init__(self) -> None:
        super().__init__()

        self._style_manager = Adw.StyleManager()
        self._style_manager.connect("notify::accent-color", self.redraw)
        self.connect("notify::progress", self.redraw)

    def redraw(self, *_) -> None:
        self.queue_draw()

    def do_measure(self, *_) -> tuple[int, int, int, int]:
        return (40, 40, -1, -1)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        size = self.get_allocated_height()
        radius = (size - 8) / 2.0

        context = snapshot.append_cairo(Graphene.Rect().init(0, 0, size, size))

        context.arc(size / 2, size / 2, radius, 0, 2 * PI)
        context.set_source_rgba(*self.get_dim_color())
        context.set_line_width(PROGRESS_RING_LINE_WIDTH)
        context.stroke()

        context.arc(size / 2, size / 2, radius, -0.5 * PI, self.progress * 2 * PI - (0.5 * PI))
        context.set_source_rgb(*self.get_accent_color())
        context.set_line_width(PROGRESS_RING_LINE_WIDTH)
        context.set_line_cap(cairo.LineCap.ROUND)
        context.stroke()

    def get_dim_color(self) -> tuple[int, int, int, int]:
        color = self.get_color()
        return color.red, color.green, color.blue, 0.15

    def get_accent_color(self) -> tuple[int, int, int]:
        color = self._style_manager.get_accent_color_rgba()
        return color.red, color.green, color.blue


class ChaptersListBox(Adw.PreferencesGroup):
    def __init__(self, title: str):
        super().__init__()
        self.set_title(title)

    def add_chapter(self, chapter: Chapter, callback: Callable[[None], None]):
        chapter_element = ChapterElement(chapter)
        chapter_element.connect("play-pause-clicked", callback)
        self.add(chapter_element)
        return chapter_element


@Gtk.Template.from_resource("/com/github/geigi/cozy/ui/book_detail.ui")
class BookDetailView(Adw.NavigationPage):
    __gtype_name__ = "BookDetail"

    play_button: Gtk.Button = Gtk.Template.Child()
    play_icon: Adw.ButtonContent = Gtk.Template.Child()

    book_label: Gtk.Label = Gtk.Template.Child()
    author_label: Gtk.Label = Gtk.Template.Child()
    total_label: Gtk.Label = Gtk.Template.Child()
    remaining_label: Gtk.Label = Gtk.Template.Child()

    book_progress_ring: ProgressRing = Gtk.Template.Child()

    album_art: Gtk.Picture = Gtk.Template.Child()
    album_art_container: Gtk.Stack = Gtk.Template.Child()
    fallback_icon: Gtk.Image = Gtk.Template.Child()

    unavailable_banner: Adw.Banner = Gtk.Template.Child()

    chapters_stack: Gtk.Stack = Gtk.Template.Child()
    chapter_list_container: Gtk.Box = Gtk.Template.Child()

    book_title = GObject.Property(type=str)

    _view_model: BookDetailViewModel = inject.attr(BookDetailViewModel)
    _artwork_cache: ArtworkCache = inject.attr(ArtworkCache)
    _toaster: ToastNotifier = inject.attr(ToastNotifier)

    _current_selected_chapter: ChapterElement | None = None

    def __init__(self):
        super().__init__()

        self._chapters_event = Event()
        self._chapters_thread: Thread | None = None
        self._chapters_job_locked = False

        self._chapter_listboxes: list[ChaptersListBox] = []
        self._chapter_elements: list[ChapterElement] = []

        self._connect_view_model()
        self._connect_widgets()

        menu_action_group = Gio.SimpleActionGroup()
        self.insert_action_group("book_overview", menu_action_group)

        self.available_offline_action = Gio.SimpleAction.new_stateful(
            "download", None, GLib.Variant.new_boolean(False)
        )
        self.available_offline_action.connect("change-state", self._download_switch_changed)
        menu_action_group.add_action(self.available_offline_action)

    def _connect_view_model(self):
        self._view_model.bind_to("book", self._on_book_changed)
        self._view_model.bind_to("playing", self._on_play_changed)
        self._view_model.bind_to("is_book_available", self._on_book_available_changed)
        self._view_model.bind_to("downloaded", self._set_book_download_status)
        self._view_model.bind_to("current_chapter", self._on_current_chapter_changed)
        self._view_model.bind_to("length", self._on_length_changed)
        self._view_model.bind_to("progress", self._on_progress_changed)
        self._view_model.bind_to("playback_speed", self._on_progress_changed)
        self._view_model.bind_to("lock_ui", self._on_lock_ui_changed)

    def _connect_widgets(self):
        self.play_button.connect("clicked", self._play_book_clicked)

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

        self.total_label.set_visible(False)
        self.unavailable_banner.set_revealed(False)

        self.book_title = book.name
        self.author_label.set_text(book.author)

        self._set_cover_image(book)
        self._on_progress_changed()
        self._display_external_section()

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
        self.unavailable_banner.set_revealed(not self._view_model.is_book_available)

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

    def _on_length_changed(self):
        self.total_label.set_text(self._view_model.total_text)

    def _on_progress_changed(self):
        self.remaining_label.set_text(self._view_model.remaining_text)
        self.book_progress_ring.progress = self._view_model.progress_percent

    def _on_lock_ui_changed(self):
        self.available_offline_action.set_enabled(not self._view_model.lock_ui)

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
        self.available_offline_action.set_enabled(external)

        if external:
            self.available_offline_action.handler_block_by_func(self._download_switch_changed)
            self.available_offline_action.set_state(
                GLib.Variant.new_boolean(self._view_model.book.offline)
            )
            self.available_offline_action.handler_unblock_by_func(self._download_switch_changed)

    def _set_cover_image(self, book: Book):

        paintable = self._artwork_cache.get_cover_paintable(
            book, self.get_scale_factor(), ALBUM_ART_SIZE
        )

        if paintable:
            self.album_art.set_paintable(paintable)
            self.album_art.set_overflow(True)
            self.album_art_container.set_visible_child(self.album_art)
        else:
            self.fallback_icon.set_from_icon_name("book-open-variant-symbolic")
            self.album_art_container.set_visible_child(self.fallback_icon)

    def _interrupt_chapters_jobs(self):
        self._chapters_job_locked = True

        if self._chapters_thread:
            self._chapters_thread.join(timeout=0.2)

    def _set_book_download_status(self):
        if not self._view_model.is_book_external:
            return

        # TODO: show this only after download
        # if self._view_model.book.downloaded:
        #     self._toaster.show(_("{book_title} is now available offline").format(book_title=self._view_model.book.name))

    def _download_switch_changed(self, action, value):
        action.set_state(value)
        self._view_model.download_book(value.get_boolean())
        self._set_book_download_status()

    def _play_chapter_clicked(self, _, chapter: Chapter):
        self._view_model.play_chapter(chapter)

    def _play_book_clicked(self, _):
        self._view_model.play_book()

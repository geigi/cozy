import logging

import gi

from cozy.control.artwork_cache import ArtworkCache
from cozy.db.book import Book
from cozy.ext import inject
from cozy.ui.widgets.playback_speed_popover import PlaybackSpeedPopover
from cozy.ui.widgets.seek_bar import SeekBar
from cozy.ui.widgets.sleep_timer import SleepTimer
from cozy.view_model.headerbar_view_model import HeaderbarViewModel, HeaderBarState
from cozy.view_model.playback_control_view_model import PlaybackControlViewModel

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from gi.repository.Handy import HeaderBar

log = logging.getLogger("Headerbar")

COVER_SIZE = 45


@Gtk.Template.from_resource('/com/github/geigi/cozy/headerbar.ui')
class Headerbar(HeaderBar):
    __gtype_name__ = "Headerbar"

    seek_bar: SeekBar = Gtk.Template.Child()

    play_button: Gtk.Button = Gtk.Template.Child()
    prev_button: Gtk.Button = Gtk.Template.Child()
    volume_button: Gtk.VolumeButton = Gtk.Template.Child()

    cover_img: Gtk.Image = Gtk.Template.Child()
    cover_img_event_box: Gtk.EventBox = Gtk.Template.Child()
    title_label: Gtk.Label = Gtk.Template.Child()
    subtitle_label: Gtk.Label = Gtk.Template.Child()

    playback_speed_button: Gtk.MenuButton = Gtk.Template.Child()
    timer_button: Gtk.MenuButton = Gtk.Template.Child()
    search_button: Gtk.MenuButton = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()

    status_stack: Gtk.Stack = Gtk.Template.Child()
    spinner: Gtk.Spinner = Gtk.Template.Child()
    status_label: Gtk.Label = Gtk.Template.Child()
    status_progress_bar: Gtk.ProgressBar = Gtk.Template.Child()

    timer_image: Gtk.Image = Gtk.Template.Child()

    play_img: Gtk.Image = Gtk.Template.Child()

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._header_container: Gtk.Box = main_window_builder.get_object("header_container")
        self._header_container.add(self)

        self.sleep_timer: SleepTimer = SleepTimer(self.timer_image)
        self.volume_button.get_style_context().remove_class("flat")
        self.playback_speed_button.set_popover(PlaybackSpeedPopover())
        self.timer_button.set_popover(self.sleep_timer)

        self._playback_control_view_model: PlaybackControlViewModel = inject.instance(PlaybackControlViewModel)
        self._headerbar_view_model: HeaderbarViewModel = inject.instance(HeaderbarViewModel)
        self._artwork_cache: ArtworkCache = inject.instance(ArtworkCache)
        self._init_app_menu()
        self._connect_view_model()
        self._connect_widgets()

        self._on_book_changed()
        self._on_lock_ui_changed()
        self._on_length_changed()
        self._on_position_changed()
        self._on_volume_changed()

    def _connect_view_model(self):
        self._playback_control_view_model.bind_to("book", self._on_book_changed)
        self._playback_control_view_model.bind_to("playing", self._on_play_changed)
        self._playback_control_view_model.bind_to("length", self._on_length_changed)
        self._playback_control_view_model.bind_to("position", self._on_position_changed)
        self._playback_control_view_model.bind_to("lock_ui", self._on_lock_ui_changed)
        self._playback_control_view_model.bind_to("volume", self._on_volume_changed)
        self._headerbar_view_model.bind_to("lock_ui", self._on_lock_ui_changed)
        self._headerbar_view_model.bind_to("state", self._on_state_changed)
        self._headerbar_view_model.bind_to("work_message", self._on_work_message_changed)
        self._headerbar_view_model.bind_to("work_progress", self._on_work_progress_changed)

    def _connect_widgets(self):
        self.play_button.connect("clicked", self._play_clicked)
        self.prev_button.connect("clicked", self._rewind_clicked)
        self.volume_button.connect("value-changed", self._on_volume_button_changed)
        self.seek_bar.connect("position-changed", self._on_seek_bar_position_changed)
        self.cover_img_event_box.connect("button-press-event", self._cover_clicked)
        self.cover_img_event_box.connect("enter-notify-event", self._on_cover_enter_notify)
        self.cover_img_event_box.connect("leave-notify-event", self._on_cover_leave_notify)

    def _init_app_menu(self):
        self.menu_builder = Gtk.Builder.new_from_resource("/com/github/geigi/cozy/titlebar_menu.ui")
        menu = self.menu_builder.get_object("titlebar_menu")
        self.menu_button.set_menu_model(menu)

    def _set_cover_image(self, book: Book):
        pixbuf = self._artwork_cache.get_cover_pixbuf(book.db_object, self.get_scale_factor(), COVER_SIZE)
        if pixbuf:
            surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.get_scale_factor(), None)
            self.cover_img.set_from_surface(surface)
        else:
            self.cover_img.set_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.DIALOG)
            self.cover_img.props.pixel_size = COVER_SIZE

    def _on_book_changed(self):
        book = self._playback_control_view_model.book
        if book:
            visibility = True
            self._set_book()
        else:
            visibility = False

        self._show_media_information(visibility)

    def _show_media_information(self, visibility):
        self.title_label.set_visible(visibility)
        self.subtitle_label.set_visible(visibility)
        self.cover_img.set_visible(visibility)
        self.seek_bar.visible = visibility

    def _set_book(self):
        book = self._playback_control_view_model.book

        self._set_cover_image(book)
        self.title_label.set_text(book.name)
        self.subtitle_label.set_text(book.current_chapter.name)

    def _on_play_changed(self):
        playing = self._playback_control_view_model.playing

        play_button_img = "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"
        self.play_img.set_from_icon_name(play_button_img, Gtk.IconSize.BUTTON)

    def _on_position_changed(self):
        position = self._playback_control_view_model.position
        if position is not None:
            self.seek_bar.position = position

    def _on_length_changed(self):
        length = self._playback_control_view_model.length
        if length:
            self.seek_bar.length = length

    def _on_lock_ui_changed(self):
        sensitive = not self._playback_control_view_model.lock_ui
        self.seek_bar.sensitive = sensitive
        self.prev_button.set_sensitive(sensitive)
        self.play_button.set_sensitive(sensitive)
        self.volume_button.set_sensitive(sensitive)
        self.playback_speed_button.set_sensitive(sensitive)
        self.timer_button.set_sensitive(sensitive)

    def _on_state_changed(self):
        if self._headerbar_view_model.state == HeaderBarState.PLAYING:
            stack_child = "playback"
            spinner_visible = False
            self.spinner.stop()
        else:
            stack_child = "working"
            spinner_visible = True
            self.spinner.start()

        self.status_stack.props.visible_child_name = stack_child
        self.spinner.set_visible(spinner_visible)

    def _on_work_message_changed(self):
        self.status_label.set_text(self._headerbar_view_model.work_message)

    def _on_work_progress_changed(self):
        self.status_progress_bar.set_fraction(self._headerbar_view_model.work_progress)

    def _on_volume_changed(self):
        self.volume_button.set_value(self._playback_control_view_model.volume)

    def _play_clicked(self, _):
        self._playback_control_view_model.play_pause()

    def _rewind_clicked(self, _):
        self._playback_control_view_model.rewind()

    def _cover_clicked(self, _, __):
        self._playback_control_view_model.open_book_detail()

    def _on_cover_enter_notify(self, widget: Gtk.Widget, __):
        widget.props.window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

    def _on_cover_leave_notify(self, widget: Gtk.Widget, __):
        widget.props.window.set_cursor(None)

    def _on_volume_button_changed(self, _, volume):
        self._playback_control_view_model.volume = volume

    def _on_seek_bar_position_changed(self, _, position):
        self._playback_control_view_model.position = position

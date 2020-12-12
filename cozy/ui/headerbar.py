import logging

import gi

from cozy.control.artwork_cache import ArtworkCache
from cozy.db.book import Book
from cozy.ext import inject
from cozy.ui.widgets.playback_speed_popover import PlaybackSpeedPopover
from cozy.ui.widgets.seek_bar import SeekBar
from cozy.view_model.headerbar_view_model import HeaderbarViewModel
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
    title_label: Gtk.Label = Gtk.Template.Child()
    subtitle_label: Gtk.Label = Gtk.Template.Child()

    playback_speed_button: Gtk.MenuButton = Gtk.Template.Child()
    timer_button: Gtk.MenuButton = Gtk.Template.Child()
    search_button: Gtk.MenuButton = Gtk.Template.Child()
    menu_button: Gtk.MenuButton = Gtk.Template.Child()

    play_img: Gtk.Image = Gtk.Template.Child()

    def __init__(self, main_window_builder: Gtk.Builder):
        super().__init__()

        self._header_container: Gtk.Box = main_window_builder.get_object("header_container")
        self._header_container.add(self)

        self.volume_button.get_style_context().remove_class("flat")

        self.playback_speed_button.set_popover(PlaybackSpeedPopover())

        self._playback_control_view_model: PlaybackControlViewModel = inject.instance(PlaybackControlViewModel)
        self._headerbar_view_model: HeaderbarViewModel = inject.instance(HeaderbarViewModel)
        self._artwork_cache: ArtworkCache = inject.instance(ArtworkCache)
        self._connect_view_model()
        self._connect_widgets()

    def _connect_view_model(self):
        self._playback_control_view_model.bind_to("book", self._on_book_changed)
        self._playback_control_view_model.bind_to("playing", self._on_play_changed)
        self._playback_control_view_model.bind_to("length", self._on_length_changed)
        self._playback_control_view_model.bind_to("position", self._on_position_changed)
        self._playback_control_view_model.bind_to("lock_ui", self._on_lock_ui_changed)
        self._playback_control_view_model.bind_to("volume", self._on_volume_changed)
        self._headerbar_view_model.bind_to("lock_ui", self._on_headerbar_lock_ui_changed)

    def _connect_widgets(self):
        self.play_button.connect("clicked", self._play_clicked)
        self.prev_button.connect("clicked", self._rewind_clicked)
        self.volume_button.connect("value-changed", self._on_volume_button_changed)
        self.seek_bar.connect("position-changed", self._on_seek_bar_position_changed)

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
        if not book:
            return

        self._set_cover_image(book)
        self.title_label.set_text(book.name)
        self.subtitle_label.set_text(book.current_chapter.name)

    def _on_play_changed(self):
        playing = self._playback_control_view_model.playing

        play_button_img = "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"
        self.play_img.set_from_icon_name(play_button_img, Gtk.IconSize.BUTTON)

    def _on_position_changed(self):
        self.seek_bar.position = self._playback_control_view_model.position

    def _on_length_changed(self):
        self.seek_bar.length = self._playback_control_view_model.length

    def _on_lock_ui_changed(self):
        sensitive = not self._playback_control_view_model.lock_ui
        self.seek_bar.sensitive = sensitive
        self.prev_button.set_sensitive(sensitive)
        self.play_button.set_sensitive(sensitive)
        self.volume_button.set_sensitive(sensitive)
        self.playback_speed_button.set_sensitive(sensitive)
        self.timer_button.set_sensitive(sensitive)

    def _on_headerbar_lock_ui_changed(self):
        sensitive = not self._headerbar_view_model.lock_ui

    def _on_volume_changed(self):
        self.volume_button.set_value(self._playback_control_view_model.volume)

    def _play_clicked(self, _):
        self._playback_control_view_model.play_pause()

    def _rewind_clicked(self, _):
        self._playback_control_view_model.rewind()

    def _on_volume_button_changed(self, _, volume):
        self._playback_control_view_model.volume = volume

    def _on_seek_bar_position_changed(self, _, position):
        self._playback_control_view_model.position = position

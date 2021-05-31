from cozy.control.artwork_cache import ArtworkCache
from cozy.db.book import Book
from cozy.ext import inject

from gi.repository import Gtk, GObject


ALBUM_ART_SIZE = 180
PLAY_BUTTON_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR


@Gtk.Template.from_resource('/com/github/geigi/cozy/album_element.ui')
class AlbumElement(Gtk.Box):
    __gtype_name__ = "AlbumElement"

    artwork_cache: ArtworkCache = inject.attr(ArtworkCache)

    button_image: Gtk.Image = Gtk.Template.Child()
    album_art_image: Gtk.Image = Gtk.Template.Child()
    play_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, book: Book):
        super().__init__()

        self._book: Book = book
        pixbuf = self.artwork_cache.get_cover_pixbuf(book, self.get_scale_factor(), ALBUM_ART_SIZE)

        if pixbuf:
            self.album_art_image.set_from_pixbuf(pixbuf)
        else:
            self.album_art_image.set_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.DIALOG)
            self.album_art_image.props.pixel_size = ALBUM_ART_SIZE

        self.play_button.connect("clicked", self._on_play_button_press)

    def set_playing(self, playing: bool):
        if playing:
            self.button_image.set_from_icon_name("media-playback-pause-symbolic", PLAY_BUTTON_ICON_SIZE)
        else:
            self.button_image.set_from_icon_name("media-playback-start-symbolic", PLAY_BUTTON_ICON_SIZE)

    def _on_play_button_press(self, _):
        self.emit("play-pause-clicked", self._book)
        return True

GObject.type_register(AlbumElement)
GObject.signal_new('play-pause-clicked', AlbumElement, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT,
                   (GObject.TYPE_PYOBJECT,))

from gi.repository import Gtk


INTRODUCED = "0.9"

@Gtk.Template.from_resource('/com/github/geigi/cozy/whats_new_library.ui')
class WhatsNewLibrary(Gtk.Box):
    __gtype_name__ = "WhatsNewLibrary"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

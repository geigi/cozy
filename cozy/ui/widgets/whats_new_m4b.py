import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


INTRODUCED = "0.7.2"


@Gtk.Template.from_resource('/com/github/geigi/cozy/whats_new_m4b.ui')
class WhatsNewM4B(Gtk.Box):
    __gtype_name__ = "WhatsNewM4B"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

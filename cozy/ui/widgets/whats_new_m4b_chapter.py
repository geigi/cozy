import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


INTRODUCED = "1.0.0"


@Gtk.Template.from_resource('/com/github/geigi/cozy/whats_new_m4b_chapter.ui')
class WhatsNewM4BChapter(Gtk.Box):
    __gtype_name__ = "WhatsNewM4BChapter"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

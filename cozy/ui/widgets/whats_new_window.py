import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


@Gtk.Template(resource_path='/com/github/geigi/cozy/whats_new.ui')
class WhatsNewWindow(Gtk.Window):
    __gtype_name__ = 'WhatsNew'

    def __init__(self, parent: Gtk.Window, **kwargs):
        super().__init__(**kwargs)
        self.set_parent(parent)
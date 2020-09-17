import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/whats_new_importer.ui')
class WhatsNewImporter(Gtk.Box):
    __gtype_name__ = "WhatsNewImporter"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

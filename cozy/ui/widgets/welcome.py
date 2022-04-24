import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/welcome.ui')
class Welcome(Gtk.Box):
    __gtype_name__ = "Welcome"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

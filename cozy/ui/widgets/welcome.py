import gi

from gi.repository import Adw, Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/welcome.ui')
class Welcome(Adw.Bin):
    __gtype_name__ = "Welcome"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

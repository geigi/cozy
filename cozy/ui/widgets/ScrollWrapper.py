import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk


class ScrollWrapper(Gtk.ScrolledWindow):
    def __init__(self, child: Gtk.Widget, **kwargs):
        super().__init__(**kwargs)
        self.show()
        self.viewport = Gtk.Viewport()
        self.viewport.show()

        self.add(self.viewport)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.viewport.add(child)

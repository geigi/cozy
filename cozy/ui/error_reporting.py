from gi.repository import Gtk


class ErrorReporting:
    def __init__(self, parent_window):
        self.builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/error_reporting.ui")
        self.window: Gtk.Window = self.builder.get_object("error_reporting_window")
        self.window.set_transient_for(parent_window)

        self.window.show()
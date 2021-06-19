import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


@Gtk.Template.from_resource('/com/github/geigi/cozy/progress_popover.ui')
class ProgressPopover(Gtk.Popover):
    __gtype_name__ = 'ProgressPopover'

    progress_label: Gtk.Label = Gtk.Template.Child()
    progress_bar: Gtk.ProgressBar = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

    def set_message(self, message: str):
        self.progress_label.set_text(message)

    def set_progress(self, progress: float):
        self.progress_bar.set_fraction(progress)

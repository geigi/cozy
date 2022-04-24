from gi.repository import Gtk


class ListBoxSeparatorRow(Gtk.ListBoxRow):
    """
    This class represents a separator in a listbox row.
    """

    def __init__(self):
        super().__init__()
        separator = Gtk.Separator()
        self.set_child(separator)
        self.set_sensitive(False)
        self.props.selectable = False
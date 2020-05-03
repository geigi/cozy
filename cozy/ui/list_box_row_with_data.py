from typing import List

from gi.repository import Gtk

from cozy.ui.list_box_separator_row import ListBoxSeparatorRow


class ListBoxRowWithData(Gtk.ListBoxRow):
    """
    This class represents a listboxitem for an author/reader.
    """
    MARGIN = 5

    def __init__(self, data, bold=False):
        super(Gtk.ListBoxRow, self).__init__()
        self.data = data
        label = Gtk.Label.new(data)
        if bold:
            label.set_markup("<b>" + data + "</b>")
        label.set_xalign(0.0)
        label.set_margin_top(self.MARGIN)
        label.set_margin_bottom(self.MARGIN)
        label.set_margin_start(7)
        self.add(label)

    def remove_all_children(self):
        self.set_visible(False)
        childs = self.get_children()
        for element in childs:
            self.remove(element)

        self.set_visible(True)

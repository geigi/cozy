from typing import List

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from cozy.ui.list_box_row_with_data import ListBoxRowWithData
from cozy.ui.list_box_separator_row import ListBoxSeparatorRow


class FilterListBox(Gtk.ListBox):
    __gtype_name__ = 'FilterListBox'

    def __init__(self, **properties):
        super().__init__(**properties)

    def populate(self, elements: List[str]):
        self.remove_all_children()

        all_row = ListBoxRowWithData(_("All"), False)
        all_row.set_tooltip_text(_("Display all books"))
        self.append(all_row)
        self.append(ListBoxSeparatorRow())
        self.select_row(all_row)

        for element in elements:
            row = ListBoxRowWithData(element, False)
            self.append(row)

    def select_row_with_content(self, row_content: str):
        for row in self.get_children():
            if not isinstance(row, ListBoxRowWithData):
                continue

            if row.data == row_content:
                self.select_row(row)
                break

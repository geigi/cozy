
from gi.repository import Gtk

from cozy.ui.list_box_row_with_data import ListBoxRowWithData


class FilterListBox(Gtk.ListBox):
    __gtype_name__ = 'FilterListBox'

    def __init__(self, **properties):
        super().__init__(**properties)

    def populate(self, elements: list[str]):
        self.remove_all()

        all_row = ListBoxRowWithData(_("All"), True)
        all_row.set_tooltip_text(_("Display all books"))
        self.append(all_row)
        self.select_row(all_row)

        for element in elements:
            row = ListBoxRowWithData(element, False)
            self.append(row)

    def select_row_with_content(self, row_content: str):
        for child in self:
            if isinstance(child, ListBoxRowWithData) and child.data == row_content:
                self.select_row(child)
                break

from gi.repository import Gtk


def remove_all_children(self):
    """
    Removes all widgets from a gtk container.
    """
    self.set_visible(False)
    childs = self.get_children()
    for element in childs:
        self.remove(element)
        element.destroy()
    self.set_visible(True)


def extend_gtk_container():
    Gtk.Container.remove_all_children = remove_all_children

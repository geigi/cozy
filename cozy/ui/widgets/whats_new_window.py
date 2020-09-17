from typing import List

import gi

from cozy.application_settings import ApplicationSettings
from cozy.ext import inject
from cozy.ui.widgets.error_reporting import ErrorReporting
from cozy.ui.widgets.whats_new_importer import WhatsNewImporter
from cozy.version import __version__ as CozyVersion

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


@Gtk.Template(resource_path='/com/github/geigi/cozy/whats_new.ui')
class WhatsNewWindow(Gtk.Window):
    __gtype_name__ = 'WhatsNew'

    content_stack: Gtk.Stack = Gtk.Template.Child()
    continue_button: Gtk.Button = Gtk.Template.Child()
    children: List[Gtk.Widget]

    app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    page = 0

    def __init__(self, parent: Gtk.Window, **kwargs):
        if self.app_settings.last_launched_version == CozyVersion:
            return

        super().__init__(**kwargs)

        self.children = [WhatsNewImporter(), ErrorReporting()]

        self.set_parent(parent)
        self.set_default_size(800, 550)

        for widget in self.children:
            self.content_stack.add(widget)

        self.continue_button.connect("clicked", self.__on_continue_clicked)
        self.show()

    def __on_continue_clicked(self, widget):
        if len(self.children) == self.page + 1:
            self.app_settings.last_launched_version = CozyVersion
            self.close()
            self.destroy()
            return

        self.page += 1
        self.content_stack.set_visible_child(self.children[self.page])

from typing import List
from packaging import version

import gi

from cozy.application_settings import ApplicationSettings
from cozy.ext import inject
from cozy.ui.main_view import CozyUI
from cozy.version import __version__ as CozyVersion

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Handy


@Gtk.Template(resource_path='/com/github/geigi/cozy/whats_new.ui')
class WhatsNewWindow(Handy.Window):
    __gtype_name__ = 'WhatsNew'

    content_stack: Gtk.Stack = Gtk.Template.Child()
    continue_button: Gtk.Button = Gtk.Template.Child()
    children: List[Gtk.Widget]

    main_window: CozyUI = inject.attr("MainWindow")
    app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    page = 0

    def __init__(self, **kwargs):
        if self.app_settings.last_launched_version == CozyVersion:
            return

        super().__init__(**kwargs)

        self.set_modal(self.main_window.window)

        self._fill_window()
        if len(self.children) < 1:
            self.end()
            return

        self.set_default_size(800, 550)

        for widget in self.children:
            self.content_stack.add(widget)
            widget.set_visible(False)

        self.children[0].set_visible(True)
        self.continue_button.connect("clicked", self.__on_continue_clicked)
        self.show()

    def _fill_window(self):
        self.children = []

        last_launched_version = self.app_settings.last_launched_version

        if last_launched_version == 'None' or last_launched_version is None:
            self._fill_welcome()
        elif type(version.parse(last_launched_version)) is version.LegacyVersion:
            self._fill_welcome()
        else:
            self._fill_whats_new(last_launched_version)

    def _fill_welcome(self):
        from cozy.ui.widgets.welcome import Welcome
        from cozy.ui.widgets.error_reporting import ErrorReporting
        self.children.append(Welcome())
        self.children.append(ErrorReporting())

    def _fill_whats_new(self, last_launched_version: version.Version):
        from cozy.ui.widgets.whats_new_m4b_chapter import INTRODUCED
        if last_launched_version < version.parse(INTRODUCED):
            from cozy.ui.widgets.whats_new_m4b_chapter import WhatsNewM4BChapter
            self.children.append(WhatsNewM4BChapter())

        from cozy.ui.widgets.whats_new_library import INTRODUCED
        if last_launched_version < version.parse(INTRODUCED):
            from cozy.ui.widgets.whats_new_library import WhatsNewLibrary
            self.children.append(WhatsNewLibrary())

        from cozy.ui.widgets.whats_new_m4b import INTRODUCED
        if last_launched_version < version.parse(INTRODUCED):
            from cozy.ui.widgets.whats_new_m4b import WhatsNewM4B
            self.children.append(WhatsNewM4B())

    def __on_continue_clicked(self, widget):
        if len(self.children) == self.page + 1:
            self.end()
            return

        self.children[self.page].set_visible(False)
        self.page += 1
        self.content_stack.set_visible_child(self.children[self.page])
        self.children[self.page].set_visible(True)

    def end(self):
        self.app_settings.last_launched_version = CozyVersion
        self.close()
        self.destroy()

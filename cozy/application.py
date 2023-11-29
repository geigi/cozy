import gettext
import locale
import logging
import os
import sys
import threading
from pathlib import Path
from traceback import format_exception

import distro

import gi

from cozy.db.storage import Storage
from cozy.ui.widgets.filter_list_box import FilterListBox
from cozy.ui.widgets.seek_bar import SeekBar

gi.require_version('Handy', '1')

from gi.repository import Gtk, GLib, Handy

from cozy.app_controller import AppController
from cozy.control.db import init_db
from cozy.control.mpris import MPRIS
from cozy.db.settings import Settings
from cozy.report import reporter
from cozy.ui.main_view import CozyUI
from cozy.version import __version__


log = logging.getLogger("application")


def setup_thread_excepthook():
    """
    Workaround for `sys.excepthook` thread bug from:
    http://bugs.python.org/issue1230540

    Call once from the main thread before creating any threads.
    """

    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):

        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    threading.Thread.__init__ = init


class Application(Gtk.Application):
    ui: CozyUI
    app_controller: AppController

    def __init__(self, localedir: str, pkgdatadir: str):
        self.localedir = localedir
        self.pkgdatadir = pkgdatadir

        Gtk.Application.__init__(self, application_id='com.github.geigi.cozy')
        self.init_custom_widgets()

        GLib.setenv("PULSE_PROP_media.role", "music", True)
        GLib.set_application_name("Cozy")

        self.old_except_hook = sys.excepthook
        sys.excepthook = self.handle_exception
        setup_thread_excepthook()

        locale.bindtextdomain('com.github.geigi.cozy', localedir)
        locale.textdomain('com.github.geigi.cozy')
        gettext.install('com.github.geigi.cozy', localedir)

    def do_startup(self):
        log.info(distro.linux_distribution(full_distribution_name=False))
        log.info("Starting up cozy " + __version__)
        self.ui = CozyUI(self.pkgdatadir, self, __version__)
        init_db()
        Gtk.Application.do_startup(self)
        Handy.init()
        try:
            manager = Handy.StyleManager.get_default()
            manager.set_color_scheme(Handy.ColorScheme.PREFER_LIGHT)
        except:
            log.info("Not setting libhandy style manager, version is too old.")
        log.info("libhandy version: {}".format(Handy._version))
        self.ui.startup()

    def do_activate(self):
        main_window_builder = self.ui.get_builder()
        self.app_controller = AppController(self, main_window_builder, self.ui)

        self.ui.activate(self.app_controller.library_view)

        if Settings.get().first_start:
            Settings.update(first_start=False).execute()

            path = os.path.join(Path.home(), _("Audiobooks"))
            Storage.create(path=path, default=True)

            os.makedirs(path, exist_ok=True)

        self.add_window(self.ui.window)
        mpris = MPRIS(self)
        mpris._on_current_changed()

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        print("handle exception")
        try:
            reporter.exception("uncaught", exc_value, "\n".join(format_exception(exc_type, exc_value, exc_traceback)))
        except:
            pass

        self.old_except_hook(exc_type, exc_value, exc_traceback)

    def quit(self):
        self.app_controller.quit()
        super(Application, self).quit()


    @staticmethod
    def init_custom_widgets():
        FilterListBox()

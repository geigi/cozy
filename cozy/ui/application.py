import locale
import logging
import os
import sys
from pathlib import Path
from traceback import format_exception

import distro
from gi.repository import Gtk, GLib

from cozy.app_controller import AppController
from cozy.control.db import init_db
from cozy.control.mpris import MPRIS
from cozy.db.settings import Settings
from cozy.media.importer import Importer
from cozy.report import reporter
from cozy.ui.main_view import CozyUI
from cozy.version import __version__


log = logging.getLogger("application")


class Application(Gtk.Application):
    ui: CozyUI
    app_controller: AppController

    def __init__(self, localedir: str, pkgdatadir: str):
        self.localedir = localedir
        self.pkgdatadir = pkgdatadir

        Gtk.Application.__init__(self, application_id='com.github.geigi.cozy')
        GLib.setenv("PULSE_PROP_media.role", "music", True)
        GLib.set_application_name("Cozy")

        self.old_except_hook = sys.excepthook
        sys.excepthook = self.handle_exception

        import gettext
        locale.bindtextdomain('com.github.geigi.cozy', localedir)
        locale.textdomain('com.github.geigi.cozy')
        gettext.install('com.github.geigi.cozy', localedir)

    def do_startup(self):
        log.info(distro.linux_distribution(full_distribution_name=False))
        log.info("Starting up cozy " + __version__)
        self.ui = CozyUI(self.pkgdatadir, self, __version__)
        init_db()
        Gtk.Application.do_startup(self)
        self.ui.startup()

    def do_activate(self):
        main_window_builder = self.ui.get_builder()
        self.app_controller = AppController(main_window_builder, self.ui)

        self.ui.activate(self.app_controller.library_view)

        if Settings.get().first_start:
            Settings.update(first_start=False).execute()
            path = str(Path.home()) + "/Audiobooks"
            Settings.update(path=str(Path.home()) + "/Audiobooks").execute()

            if not os.path.exists(path):
                os.makedirs(path)

        self.add_window(self.ui.window)
        mpris = MPRIS(self)
        mpris._on_current_changed(None)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        print("handle exception")
        try:
            reporter.exception("uncaught", exc_value, "\n".join(format_exception(exc_type, exc_value, exc_traceback)))
        except:
            pass

        self.old_except_hook(exc_type, exc_value, exc_traceback)
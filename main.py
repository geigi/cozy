#!@PYTHON@

# main.py
#
# Copyright (C) 2017 geigi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import code
import locale
import logging
import os
import signal
import sys
import traceback
import distro
from traceback import format_exception
import gi

from cozy.app_controller import AppController
from cozy.ui.widgets.filter_list_box import FilterListBox
from cozy.ui.widgets.list_box_extensions import extend_gtk_container

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')

from cozy.report import reporter
from cozy.version import __version__
from pathlib import Path
from gi.repository import Gtk, GObject, GLib
from cozy.ui.main_view import CozyUI
from cozy.control.db import init_db, Settings
from cozy.control.mpris import MPRIS

old_except_hook = None

log = logging.getLogger("main")
data_dir = os.path.join(GLib.get_user_data_dir(), "cozy")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
pkgdatadir = '@DATA_DIR@'
localedir = '@LOCALE_DIR@'
LOG_FORMAT = "%(asctime)s [%(threadName)-12.12s] [%(name)-10.10s] [%(levelname)-5.5s]  %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"

# setup log files
log1 = os.path.join(data_dir, "cozy_1.log")
log0 = os.path.join(data_dir, "cozy.log")
if os.path.exists(log1):
    os.remove(log1)
if os.path.exists(os.path.join(data_dir, "cozy.log")):
    os.rename(log0, log1)


class Application(Gtk.Application):
    def __init__(self, **kwargs):
        self.ui: CozyUI = None
        self.app_controller: AppController = None

        listen()
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
        self.ui = CozyUI(pkgdatadir, self, __version__)
        init_db()
        Gtk.Application.do_startup(self)
        self.ui.startup()

    def do_activate(self):
        main_window_builder = self.ui.get_builder()
        self.app_controller = AppController(main_window_builder)

        self.ui.activate(self.app_controller.library_view)

        if Settings.get().first_start:
            Settings.update(first_start=False).execute()
            path = str(Path.home()) + "/Audiobooks"
            Settings.update(path=str(Path.home()) + "/Audiobooks").execute()

            if not os.path.exists(path):
                os.makedirs(path)
            else:
                self.ui.scan(None, True)
                self.ui.refresh_content()

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


def __on_command_line():
    """
      Handle command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", dest="debug")
    args = parser.parse_args(sys.argv[1:])

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, handlers=[
            logging.FileHandler(log0),
            logging.StreamHandler(sys.stdout)
        ])
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, handlers=[
            logging.FileHandler(log0),
            logging.StreamHandler(sys.stdout)
        ])


def extend_classes():
    extend_gtk_container()


def init_custom_widgets():
    FilterListBox()


def main():
    __on_command_line()
    print(sys.argv)

    extend_classes()
    init_custom_widgets()

    application = Application()

    try:
        # Handle the debug option seperatly without the Glib stuff
        if "-d" in sys.argv:
            sys.argv.remove("-d")
        ret = application.run(sys.argv)
    except SystemExit as e:
        ret = e.code

    sys.exit(ret)


def debug(sig, frame):
    """Interrupt running process, and provide a python prompt for
    interactive debugging."""
    d = {'_frame': frame}  # Allow access to frame object.
    d.update(frame.f_globals)  # Unless shadowed by global
    d.update(frame.f_locals)

    i = code.InteractiveConsole(d)
    message = "Signal received : entering python shell.\nTraceback:\n"
    message += ''.join(traceback.format_stack(frame))
    i.interact(message)


def listen():
    signal.signal(signal.SIGUSR1, debug)  # Register handler


if __name__ == '__main__':
    main()

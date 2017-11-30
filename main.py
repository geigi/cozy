#!/usr/bin/env python3

# main.py
#
# Copyright (C) 2017 geigi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program  /home/ju/GitHub/Cozyis distributed in the hope that it will be useful,
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

import gi
gi.require_version('Gtk', '3.0')

from pathlib import Path
from gi.repository import Gtk, GObject, GLib
from cozy.ui import CozyUI
from cozy.db import init_db, Settings
from cozy.mpris import MPRIS

log = logging.getLogger("main")

pkgdatadir = '@DATA_DIR@'
localedir = '@LOCALE_DIR@'
version = '@VERSION@'


class Application(Gtk.Application):
    def __init__(self, **kwargs):
        self.ui = None

        GObject.threads_init()
        listen()

        Gtk.Application.__init__(self, application_id='com.github.geigi.cozy')

        GLib.setenv("PULSE_PROP_media.role", "music", True)

        import gettext

        locale.bindtextdomain('cozy', localedir)
        locale.textdomain('cozy')
        gettext.install('cozy', localedir)

    def do_startup(self):
        log.info("Starting up cozy " + version)
        self.ui = CozyUI(pkgdatadir, self, version)
        init_db()
        Gtk.Application.do_startup(self)
        self.ui.startup()

    def do_activate(self):
        self.ui.activate()

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
        MPRIS(self, self.ui)


def __on_command_line():
    """
      Handle command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", dest="debug")
    args = parser.parse_args(sys.argv[1:])

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


def main():
    __on_command_line()
    print(sys.argv)
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
    d = {'_frame': frame}         # Allow access to frame object.
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

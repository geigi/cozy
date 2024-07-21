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
import gettext
import locale
import logging
import os
import signal
import sys
import traceback

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')
gi.require_version('GstController', '1.0')
gi.require_version('GstPbutils', '1.0')

from gi.repository import Gio, GLib

pkgdatadir = '@DATA_DIR@'
localedir = '@LOCALE_DIR@'

# We need to call `locale.*textdomain` to get the strings in UI files translated
locale.bindtextdomain('com.github.geigi.cozy', localedir)
locale.textdomain('com.github.geigi.cozy')

# But also `gettext.*textdomain`, to make `_("foo")` in Python work as well
gettext.bindtextdomain('com.github.geigi.cozy', localedir)
gettext.textdomain('com.github.geigi.cozy')

gettext.install('com.github.geigi.cozy', localedir)


# gresource must be registered before importing any Gtk.Template annotated classes
resource = Gio.Resource.load(os.path.join(pkgdatadir, 'com.github.geigi.cozy.gresource'))
resource._register()

old_except_hook = None

log = logging.getLogger("main")
data_dir = os.path.join(GLib.get_user_data_dir(), "cozy")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
LOG_FORMAT = "%(asctime)s [%(threadName)-12.12s] [%(name)-10.10s] [%(levelname)-5.5s]  %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"

# setup log files
log1 = os.path.join(data_dir, "cozy_1.log")
log0 = os.path.join(data_dir, "cozy.log")
if os.path.exists(log1):
    os.remove(log1)
if os.path.exists(os.path.join(data_dir, "cozy.log")):
    os.rename(log0, log1)


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


def main():
    __on_command_line()
    print(sys.argv)

    listen()

    application = Application(pkgdatadir)

    try:
        # Handle the debug option separately without the Glib stuff
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
    import multiprocessing as mp
    mp.set_start_method('spawn')

    # All cozy imports are happening here because multiprocessing needs to be setup first
    # Some modules import multiprocessing which would lead to an exception
    # when setting the start method
    from cozy.application import Application

    main()

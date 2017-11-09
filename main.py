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

import sys
import gi
import locale
import logging
import argparse
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib, Gio

from cozy.ui import CozyUI
from cozy.db import *
from cozy.mpris import MPRIS

log = logging.getLogger("main")

pkgdatadir = '@DATA_DIR@'
localedir = '@LOCALE_DIR@'
version = '@VERSION@'

class Application(Gtk.Application):
  def __init__(self, **kwargs):
    GObject.threads_init()

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
    if Settings.get().first_start:
      self.hello = self.ui.hello_builder.get_object("hello_window")
      self.folder_chooser = self.ui.hello_builder.get_object("book_location")
      self.start_button = self.ui.hello_builder.get_object("start_button")
      self.start_button.connect("clicked", self.first_start)
      self.folder_chooser.connect("file-set", self.__on_folder_changed)
      auto_scan_switch = self.ui.hello_builder.get_object("auto_scan_switch")
      self.ui.settings.bind("autoscan", auto_scan_switch, "active", Gio.SettingsBindFlags.DEFAULT)

      self.hello.show()
      self.add_window(self.hello)

    else:
      self.ui.activate()
      self.add_window(self.ui.window)
      MPRIS(self, self.ui)

  def first_start(self, button):
    """
    Store the user selected path and start the first import.
    """
    log.info("Cozy will now import all audio files from your selected location.")

    location = self.folder_chooser.get_file().get_path()
    Settings.update(first_start = False).execute()
    Settings.update(path = location).execute()
    self.hello.close()

    self.ui.activate()
    self.ui.main_stack.props.visible_child_name = "import"
    self.add_window(self.ui.window)
    self.ui.scan(None, True)
    self.ui.refresh_content()

  def __on_folder_changed(self, sender):
    """
    Enable the start button when the user selected a location.
    """
    self.start_button.set_sensitive(True)

def __on_command_line():
    """
      Handle command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", dest="debug")
    args = parser.parse_args(sys.argv[1:])

    if args.debug == True:
      logging.basicConfig(level=logging.DEBUG)
    else:
      logging.basicConfig(level=logging.INFO)

def main():
  __on_command_line()
  print(sys.argv)
  application = Application()

  try:
    # Handle the debug option seperatly without the Glib stuff
    if "-d" in sys.argv: sys.argv.remove("-d")
    ret = application.run(sys.argv)
  except SystemExit as e:
    ret = e.code

  sys.exit(ret)

if __name__ == '__main__':
  main()
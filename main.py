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
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cozy.ui import CozyUI
from cozy.db import *

pkgdatadir = '@DATA_DIR@'

class Application(Gtk.Application):
  def __init__(self, **kwargs):
    super().__init__(application_id='org.gnome.Audiobooks', **kwargs)
    self.ui = CozyUI(pkgdatadir, self)
    InitDB()

  def do_startup(self):
    Gtk.Application.do_startup(self)
    self.ui.startup()

  def do_activate(self):
    if Settings.get().first:
      self.hello = self.ui.hello_builder.get_object("hello_window")
      self.folder_chooser = self.ui.hello_builder.get_object("book_location")
      self.start_button = self.ui.hello_builder.get_object("start_button")
      self.start_button.connect("clicked", self.first_start)
      self.folder_chooser.connect("file-set", self.__on_folder_changed)

      self.hello.show()
      self.add_window(self.hello)
    else:
      self.ui.activate()
      self.add_window(self.ui.window)

  def first_start(self, button):
    """
    Store the user selected path and start the first import.
    """
    print("Cozy will now import all audio files from your selected location.")

    location = self.folder_chooser.get_file().get_path()
    Settings.update(first = False).execute()
    Settings.update(path = location).execute()
    self.hello.close()

    self.ui.activate()
    self.add_window(self.ui.window)
    self.ui.scan(None, None)

  def __on_folder_changed(self, sender):
    """
    Enable the start button when the user selected a location.
    """
    self.start_button.set_sensitive(True)

def main():
  application = Application()

  try:
    ret = application.run(sys.argv)
  except SystemExit as e:
    ret = e.code

  sys.exit(ret)

if __name__ == '__main__':
  main()
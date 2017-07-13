#!/usr/bin/env python3

# __main__.py
#
# Copyright (C) 2017 geigi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import gi
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio

pkgdatadir = '@DATA_DIR@'

class Application(Gtk.Application):
  def __init__(self, **kwargs):
    super().__init__(application_id='org.gnome.Audiobooks', **kwargs)

  def do_activate(self):
    resource = Gio.resource_load(os.path.join(pkgdatadir, 'audiobooks.ui.gresource'))
    Gio.Resource._register(resource)

    resource = Gio.resource_load(os.path.join(pkgdatadir, 'audiobooks.img.gresource'))
    Gio.Resource._register(resource)

    builder = Gtk.Builder.new_from_resource("/de/geigi/audiobooks/main_window.ui")

    window = builder.get_object("app_window")
    window.set_application(self)
    window.present()

def main():
  application = Application()

  try:
    ret = application.run(sys.argv)
  except SystemExit as e:
    ret = e.code

  sys.exit(ret)

if __name__ == '__main__':
  main()

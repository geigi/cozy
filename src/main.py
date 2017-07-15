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
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Gdk

pkgdatadir = '@DATA_DIR@'

class ListBoxRowWithData(Gtk.ListBoxRow):
  def __init__(self, data):
    super(Gtk.ListBoxRow, self).__init__()
    self.data = data
    label = Gtk.Label(data)
    label.set_xalign(0.0)
    self.add(label)

class Application(Gtk.Application):
  def __init__(self, **kwargs):
    super().__init__(application_id='org.gnome.Audiobooks', **kwargs)

  def do_activate(self):
    self.init_resources()
    self.init_css()
    self.init_window()
    self.init_actions()

  def init_resources(self):
    resource = Gio.resource_load(os.path.join(pkgdatadir, 'cozy.ui.gresource'))
    Gio.Resource._register(resource)

    resource = Gio.resource_load(os.path.join(pkgdatadir, 'cozy.img.gresource'))
    Gio.Resource._register(resource)

  def init_css(self):
    if Gtk.get_minor_version() > 18:
      print("Fanciest design possible")
      cssProviderFile = Gio.File.new_for_uri("resource:///de/geigi/cozy/application.css")
    else :
      print("Using legacy css file")
      cssProviderFile = Gio.File.new_for_uri("resource:///de/geigi/cozy/application_legacy.css")
    cssProvider = Gtk.CssProvider()
    cssProvider.load_from_file(cssProviderFile)

    screen = Gdk.Screen.get_default()
    styleContext = Gtk.StyleContext()
    styleContext.add_provider_for_screen(screen, cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

  def init_window(self):
    window_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/main_window.ui")
    search_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/search_popover.ui")

    window = window_builder.get_object("app_window")
    window.set_application(self)
    window.show_all()
    window.present()

    # just for demo
    scale = window_builder.get_object("progress_scale")
    scale.set_range(0, 4)
    author_box = window_builder.get_object("author_box")
    reader_box = window_builder.get_object("reader_box")

    for i in range(1,100):
      row_a = ListBoxRowWithData(i)
      row_b = ListBoxRowWithData(i)

      author_box.add(row_a)
      reader_box.add(row_b)
      pass

    author_box.show_all()
    reader_box.show_all()

    search_button = window_builder.get_object("search_button")
    popover = search_builder.get_object("search_popover")

    search_button.set_popover(popover)

    self.set_app_menu(window_builder.get_object("app_menu"))

  def init_actions(self):
    help_action = Gio.SimpleAction.new("help", None)
    help_action.connect("activate", self.help)
    self.add_action(help_action)

    about_action = Gio.SimpleAction.new("about", None)
    about_action.connect("activate", self.about)
    self.add_action(about_action)

    quit_action = Gio.SimpleAction.new("quit", None)
    quit_action.connect("activate", self.quit)
    self.add_action(quit_action)

  def help(self, action, parameter):
    pass

  def quit(self, action, parameter):
      self.quit()

  def about(self, action, parameter):
    pass

def main():
  application = Application()

  try:
    ret = application.run(sys.argv)
  except SystemExit as e:
    ret = e.code

  sys.exit(ret)

if __name__ == '__main__':
  main()

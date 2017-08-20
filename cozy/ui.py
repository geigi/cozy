import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Gdk, GdkPixbuf
from threading import Thread

from cozy.importer import *
from cozy.db import *
from cozy.book_element import *

class CozyUI:
  """
  CozyUI is the main ui class.
  """
  def __init__(self, pkgdatadir, app):
    self.pkgdir = pkgdatadir
    self.app = app

  def activate(self):
    self.__init_window()
    self.__init_bindings()

    self.scan(None, None)

  def startup(self):
    self.__init_resources()
    self.__init_css()
    self.__init_actions()

  def __init_resources(self):
    """
    Initialize all resources like gresource and glade windows.
    """
    resource = Gio.resource_load(os.path.join(self.pkgdir, 'cozy.ui.gresource'))
    Gio.Resource._register(resource)

    resource = Gio.resource_load(os.path.join(self.pkgdir, 'cozy.img.gresource'))
    Gio.Resource._register(resource)

    self.window_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/main_window.ui")
    self.search_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/search_popover.ui")
    self.timer_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/timer_popover.ui")
    self.settings_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/settings.ui")
    self.menu_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/app_menu.ui")
    self.about_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/about.ui")
    self.hello_builder = Gtk.Builder.new_from_resource("/de/geigi/cozy/hello.ui")

  def __init_css(self):
    """
    Initialize the main css files and providers.
    Add css classes to the default screen style context.
    """
    if Gtk.get_minor_version() > 18:
      print("Fanciest design possible")
      cssProviderFile = Gio.File.new_for_uri("resource:///de/geigi/cozy/application.css")
    else :
      print("Using legacy css file")
      cssProviderFile = Gio.File.new_for_uri("resource:///de/geigi/cozy/application_legacy.css")
    cssProvider = Gtk.CssProvider()
    cssProvider.load_from_file(cssProviderFile)

    # add the bordered css class to the default screen for the borders around album art
    screen = Gdk.Screen.get_default()
    styleContext = Gtk.StyleContext()
    styleContext.add_provider_for_screen(screen, cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    styleContext.add_class("bordered")

  def __init_window(self):
    """
    Add fields for all ui objects we need to access from code.
    Initialize everything we can't do from glade like events and other stuff.
    """
    self.window = self.window_builder.get_object("app_window")
    self.window.set_application(self.app)
    self.window.show_all()
    self.window.present()

    search_button = self.window_builder.get_object("search_button")
    search_popover = self.search_builder.get_object("search_popover")
    timer_button = self.window_builder.get_object("timer_button")
    timer_popover = self.timer_builder.get_object("timer_popover")

    self.timer_switch = self.timer_builder.get_object("timer_switch")
    self.timer_scale = self.timer_builder.get_object("timer_scale")
    self.timer_spinner = self.timer_builder.get_object("timer_spinner")
    self.timer_buffer = self.timer_builder.get_object("timer_buffer")
    self.cover_img = self.window_builder.get_object("cover_img")
    self.throbber = self.window_builder.get_object("spinner")
    self.author_box = self.window_builder.get_object("author_box")
    self.reader_box = self.window_builder.get_object("reader_box")
    self.book_box = self.window_builder.get_object("book_box")
    self.sort_stack = self.window_builder.get_object("sort_stack")

    # get settings window
    self.settings_window = self.settings_builder.get_object("settings_window")
    self.settings_window.set_transient_for(self.window)
    self.settings_window.connect("delete-event", self.hide_window)
    self.initDbSettings()

    # get about dialog
    self.about_dialog = self.about_builder.get_object("about_dialog")
    self.about_dialog.set_transient_for(self.window)
    self.about_dialog.connect("delete-event", self.hide_window)

    # we need to update the database when the audio book location was changed
    folder_chooser = self.settings_builder.get_object("location_chooser")
    folder_chooser.connect("file-set", self.__on_folder_changed)

    # init popovers
    search_button.set_popover(search_popover)
    timer_button.set_popover(timer_popover)

    # add marks to timer scale
    for i in range(0, 181, 15):
      self.timer_scale.add_mark(i, Gtk.PositionType.RIGHT, None)

    # timer SpinButton text format
    self.timer_spinner.connect("value-changed", self.__on_timer_changed)
    # this is required otherwise the timer will not show "min" on start
    self.__init_timer_buffer()

    # shortcuts
    self.accel = Gtk.AccelGroup()

    # sorting and filtering
    self.author_box.connect("row-activated", self.__on_listbox_changed)
    self.reader_box.connect("row-activated", self.__on_listbox_changed)
    self.book_box.set_sort_func(self.__sort_books, None, False)
    self.book_box.set_filter_func(self.__filter_books, None, False)
    self.book_box.connect("selected-children-changed", self.__on_book_selec_changed)

    # DEMO #
    scale = self.window_builder.get_object("progress_scale")
    scale.set_range(0, 4)

    pixbuf = GdkPixbuf.Pixbuf.new_from_resource("/de/geigi/cozy/blank_album.png")
    self.set_title_cover(pixbuf)

  def __init_actions(self):
    """
    Init all app actions.
    """
    self.accel = Gtk.AccelGroup()

    menu = self.menu_builder.get_object("app_menu")
    self.app.set_app_menu(menu)

    help_action = Gio.SimpleAction.new("help", None)
    help_action.connect("activate", self.help)
    self.app.add_action(help_action)

    about_action = Gio.SimpleAction.new("about", None)
    about_action.connect("activate", self.about)
    self.app.add_action(about_action)

    quit_action = Gio.SimpleAction.new("quit", None)
    quit_action.connect("activate", self.quit)
    self.app.add_action(quit_action)
    self.app.set_accels_for_action("app.quit", ["<Control>q", "<Control>w"])

    pref_action = Gio.SimpleAction.new("prefs", None)
    pref_action.connect("activate", self.show_prefs)
    self.app.add_action(pref_action)
    self.app.set_accels_for_action("app.prefs", ["<Control>comma"])

    scan_action = Gio.SimpleAction.new("scan", None)
    scan_action.connect("activate", self.scan)
    self.app.add_action(scan_action)

  def __init_bindings(self):
    """
    Bind Gio.Settings to widgets in settings dialog.
    """
    settings = Gio.Settings.new("de.geigi.Cozy")

    sl_switch = self.settings_builder.get_object("symlinks_switch")
    settings.bind("symlinks", sl_switch, "active", Gio.SettingsBindFlags.DEFAULT)

    auto_scan_switch = self.settings_builder.get_object("auto_scan_switch")
    settings.bind("autoscan", auto_scan_switch, "active", Gio.SettingsBindFlags.DEFAULT)

    timer_suspend_switch = self.settings_builder.get_object("timer_suspend_switch")
    settings.bind("suspend", timer_suspend_switch, "active", Gio.SettingsBindFlags.DEFAULT)

    replay_switch = self.settings_builder.get_object("replay_switch")
    settings.bind("replay", replay_switch, "active", Gio.SettingsBindFlags.DEFAULT)

  def __init_timer_buffer(self):
    """
    Add "min" to the timer text field on startup.
    """
    adjustment = self.timer_spinner.get_adjustment()
    value = adjustment.get_value()

    text = str(int(value)) + " min"
    self.timer_buffer.set_text(text, len(text))

    return True

  def help(self, action, parameter):
    """
    Show app help.
    """
    pass

  def quit(self, action, parameter):
    """
    Quit app.
    """
    self.app.quit()

  def about(self, action, parameter):
    """
    Show about window.
    """
    self.about_dialog.show()
    pass

  def show_prefs(self, action, parameter):
    """
    Show preferences window.
    """
    self.settings_window.show()
    pass

  def hide_window(self, widget, data=None):
    """
    Hide a given window. This is used for the about and settings dialog
    as they will never be closed only hidden.

    param widget: The widget that will be hidden.
    """
    widget.hide()

    # we handeled the close event so the window must not get destroyed.
    return True

  def set_title_cover(self, pixbuf):
    """
    Sets the cover in the title bar.
    """
    pixbuf = pixbuf.scale_simple(40, 40, GdkPixbuf.InterpType.BILINEAR)
    self.cover_img.set_from_pixbuf(pixbuf)

  def scan(self, action, parameter):
    """
    Start the db import in a seperate thread
    """
    thread = Thread(target = Import, args=(self, ))
    thread.start()
    pass

  def initDbSettings(self):
    """
    Display settings from the database in the ui.
    """
    chooser = self.settings_builder.get_object("location_chooser")
    chooser.set_current_folder(Settings.get().path)

  def refresh_content(self):
    """
    Refresh all content.
    """
    # First clear the boxes
    childs = self.author_box.get_children()
    for element in childs:
      self.author_box.remove(element)

    childs = self.reader_box.get_children()
    for element in childs:
      self.reader_box.remove(element)

    childs = self.book_box.get_children()
    for element in childs:
      self.book_box.remove(element)

    # we want every item only once, so wh use a list to add only the new ones
    seen_authors = []
    seen_readers = []
    for book in Books():
      if book.author not in seen_authors:
        seen_authors.append(book.author)

      if book.reader not in seen_readers:
        seen_readers.append(book.reader)
      pass

    seen_authors.sort()
    seen_readers.sort()

    # TODO translate
    # Add the special All element
    all_row = ListBoxRowWithData("All")
    self.author_box.add(all_row)
    self.author_box.select_row(all_row)
    all_row = ListBoxRowWithData("All")
    self.reader_box.add(all_row)
    self.reader_box.select_row(all_row)

    for author in seen_authors:
      row = ListBoxRowWithData(author)
      self.author_box.add(row)

    for reader in seen_readers:
      row = ListBoxRowWithData(reader)
      self.reader_box.add(row)

    # this is required to see the new items
    self.author_box.show_all()
    self.reader_box.show_all()

    for b in Books():
      self.book_box.add(BookElement(b))
      pass

    self.book_box.show_all()

  def __on_timer_changed(self, spinner):
    """
    Add "min" to the timer text box on change.
    """
    if not self.timer_switch.get_active():
      self.timer_switch.set_active(True)

    adjustment = self.timer_spinner.get_adjustment()
    value = adjustment.get_value()

    text = str(int(value)) + " min"
    self.timer_buffer.set_text(text, len(text))

  def __on_folder_changed(self, sender):
    """
    Clean the database when the audio book location is changed.
    """
    print("Change folder")
    folder_chooser = self.settings_builder.get_object("location_chooser")
    settings = Settings.get()
    settings.path = folder_chooser.get_file().get_path()
    settings.save()
    CleanDB()
    self.scan(None, None)

  def __on_book_selec_changed(self, flowbox):
    """
    Fix the overlay on the selected book.
    """
    if len(flowbox.get_selected_children()) > 0:
      selected = flowbox.get_selected_children()[0]
      for child in flowbox.get_children():
        if child == selected:
          child.get_children()[0].selected = True
        else:
          child.get_children()[0].selected = False
          child.get_children()[0]._on_leave_notify(None, None)

  ####################
  # CONTENT HANDLING #
  ####################

  def __on_listbox_changed(self, sender, row):
    """
    Refresh the filtering on author/reader selection.
    """
    self.book_box.invalidate_filter();

  def __sort_books(self, book_1, book_2, data, notify_destroy):
    """
    Sort books alphabetically by name.
    """
    return book_1.get_children()[0].book.name.lower() > book_2.get_children()[0].book.name.lower()

  def __filter_books(self, book, data, notify_destroy):
    """
    Filter the books in the book view according to the selected author/reader or "All".
    """
    if self.sort_stack.get_visible_child().get_name() == "sort_author_scroller":
      author = self.author_box.get_selected_row().data
      if author is None:
        return True

      if author == "All":
        return True
      else:
        return True if book.get_children()[0].book.author == author else False
    else:
      reader = self.reader_box.get_selected_row().data
      if reader is None:
        return True
        
      if reader == "All":
        return True
      else:
        return True if book.get_children()[0].book.reader == reader else False


class ListBoxRowWithData(Gtk.ListBoxRow):
  """
  This class represents a listboxitem for an author/reader.
  """
  MARGIN = 5
  def __init__(self, data):
    super(Gtk.ListBoxRow, self).__init__()
    self.data = data
    label = Gtk.Label(data)
    label.set_xalign(0.0)
    label.set_margin_top(self.MARGIN)
    label.set_margin_bottom(self.MARGIN)
    self.add(label)
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Gdk, GdkPixbuf, Pango
from threading import Thread

from cozy.importer import *
from cozy.db import *

class CozyUI:
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

  def __init_css(self):
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
    styleContext.add_class("bordered")

  def __init_window(self):
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


    # init popovers
    search_button.set_popover(search_popover)
    timer_button.set_popover(timer_popover)

    # add marks to timer scale
    for i in range(0, 181, 15):
      self.timer_scale.add_mark(i, Gtk.PositionType.RIGHT, None)

    # timer SpinButton text format
    self.timer_spinner.connect("value-changed", self.__on_timer_changed)
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

  def help(self, action, parameter):
    pass

  def quit(self, action, parameter):
      self.app.quit()

  def about(self, action, parameter):
    self.about_dialog.show()
    pass

  def show_prefs(self, action, parameter):
    self.settings_window.show()
    pass

  def hide_window(self, widget, data=None):
    widget.hide()

    return True

  def set_title_cover(self, pixbuf):
    pixbuf = pixbuf.scale_simple(40, 40, GdkPixbuf.InterpType.BILINEAR)
    self.cover_img.set_from_pixbuf(pixbuf)

  def scan(self, action, parameter):
    thread = Thread(target = Import, args=(self, ))
    thread.start()
    pass

  def initDbSettings(self):
    chooser = self.settings_builder.get_object("location_chooser")
    chooser.set_current_folder(Settings.get().path)

  def refresh_content(self):
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



    self.author_box.show_all()
    self.reader_box.show_all()

    for b in Books():
        self.book_box.add(BookElement(b))
        pass

    self.book_box.show_all()

  def __init_bindings(self):
    settings = Gio.Settings.new("de.geigi.Cozy")

    sl_switch = self.settings_builder.get_object("symlinks_switch")
    settings.bind("symlinks", sl_switch, "active", Gio.SettingsBindFlags.DEFAULT)

    auto_scan_switch = self.settings_builder.get_object("auto_scan_switch")
    settings.bind("autoscan", auto_scan_switch, "active", Gio.SettingsBindFlags.DEFAULT)

    timer_suspend_switch = self.settings_builder.get_object("timer_suspend_switch")
    settings.bind("suspend", timer_suspend_switch, "active", Gio.SettingsBindFlags.DEFAULT)

    replay_switch = self.settings_builder.get_object("replay_switch")
    settings.bind("replay", replay_switch, "active", Gio.SettingsBindFlags.DEFAULT)

    folder_chooser = self.settings_builder.get_object("location_chooser")
    folder_chooser.connect("file-set", self.__on_folder_changed)

  def __init_timer_buffer(self):
    adjustment = self.timer_spinner.get_adjustment()
    value = adjustment.get_value()

    text = str(int(value)) + " min"
    self.timer_buffer.set_text(text, len(text))

    return True

  def __on_timer_changed(self, spinner):
    if not self.timer_switch.get_active():
      self.timer_switch.set_active(True)

    adjustment = self.timer_spinner.get_adjustment()
    value = adjustment.get_value()

    text = str(int(value)) + " min"
    self.timer_buffer.set_text(text, len(text))

  def __on_folder_changed(self, sender):
    folder_chooser = self.settings_builder.get_object("location_chooser")
    settings = Settings.get()
    settings.path = folder_chooser.get_file().get_path()
    settings.save()
    CleanDB()

  def __on_book_selec_changed(self, flowbox):
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
    self.book_box.invalidate_filter();

  def __sort_books(self, book_1, book_2, data, notify_destroy):
    return book_1.get_children()[0].book.name.lower() > book_2.get_children()[0].book.name.lower()

  def __filter_books(self, book, data, notify_destroy):
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
  MARGIN = 5
  def __init__(self, data):
    super(Gtk.ListBoxRow, self).__init__()
    self.data = data
    label = Gtk.Label(data)
    label.set_xalign(0.0)
    label.set_margin_top(self.MARGIN)
    label.set_margin_bottom(self.MARGIN)
    self.add(label)

class BookElement(Gtk.Box):
  book = None
  selected = False
  def __init__(self, b):
    self.book = b

    super(Gtk.Box, self).__init__()
    self.set_orientation(Gtk.Orientation.VERTICAL)
    self.set_spacing(10)
    self.set_halign(Gtk.Align.CENTER)
    self.set_valign(Gtk.Align.START)
    self.set_margin_top(10)

    label = Gtk.Label((self.book.name[:60] + '...') if len(self.book.name) > 60 else self.book.name)
    label.set_xalign(0.5)
    label.set_line_wrap(Pango.WrapMode.WORD_CHAR)
    label.props.max_width_chars = 30
    label.props.justify = Gtk.Justification.CENTER

    if self.book.cover is not None:
        loader = GdkPixbuf.PixbufLoader.new_with_type("jpeg")
        loader.write(b.cover)
        loader.close()
        pixbuf = loader.get_pixbuf()
    else:
        pixbuf = GdkPixbuf.Pixbuf.new_from_resource("/de/geigi/cozy/blank_album.png")

    pixbuf = pixbuf.scale_simple(180, 180, GdkPixbuf.InterpType.BILINEAR)
    
    box = Gtk.EventBox()
    box.set_halign(Gtk.Align.CENTER)
    box.set_valign(Gtk.Align.CENTER)

    img = Gtk.Image()
    img.set_halign(Gtk.Align.CENTER)
    img.set_valign(Gtk.Align.CENTER)
    img.get_style_context().add_class("bordered")
    img.set_from_pixbuf(pixbuf)

    play_img = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.DIALOG)
    play_img.get_style_context().add_class("white")

    play_color = Gtk.Grid()
    play_color.get_style_context().add_class("black_opacity")
    play_color.set_property("halign", Gtk.Align.CENTER)
    play_color.set_property("valign", Gtk.Align.CENTER)
    play_color.add(play_img)

    self.overlay = Gtk.Overlay.new()
    self.overlay.add(img)
    self.play_overlay = Gtk.Overlay.new()
    self.play_overlay.add(play_color)
    self.play_overlay.set_opacity(0.0)
    self.overlay.add_overlay(self.play_overlay)
    
    color = Gtk.Grid()
    color.get_style_context().add_class("mouse_hover")
    color.set_property("halign", Gtk.Align.CENTER)
    color.set_property("valign", Gtk.Align.CENTER)
    color.add(self.overlay)

    box.add(color)
    self.add(box)
    box.connect("enter-notify-event", self._on_enter_notify)
    box.connect("leave-notify-event", self._on_leave_notify)
    box.connect("button-press-event", self.__on_button_press)

    self.add(label)

  def __on_button_press(self, eventbox, event):
    pass

  def _on_enter_notify(self, widget, event):
    """
      On enter notify, change overlay opacity
      @param widget as Gtk.EventBox
      @param event as Gdk.Event
    """
    self.overlay.set_opacity(0.85)
    self.play_overlay.set_opacity(1.0)

  def _on_leave_notify(self, widget, event):
    """
      On leave notify, change overlay opacity
      @param widget as Gtk.EventBox (can be None)
      @param event as Gdk.Event (can be None)
    """
    if not self.selected:
      self.overlay.set_opacity(1.0)
      self.play_overlay.set_opacity(0.0)
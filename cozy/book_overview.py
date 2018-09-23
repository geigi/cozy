from gi.repository import Gtk, Gdk, Gst

import cozy.artwork_cache as artwork_cache
import cozy.db as db
import cozy.tools as tools
import cozy.player as player
import cozy.ui

from cozy.book_element import TrackElement
from cozy.settings import Settings
from cozy.offline_cache import OfflineCache
from cozy.disk_element import DiskElement


class BookOverview:
    """
    This class contains all logic for the book overview.
    """
    book = None
    current_track_element = None
    switch_signal = None

    def __init__(self):
        self.ui = cozy.ui.CozyUI()
        builder = self.ui.window_builder
        self.name_label = builder.get_object("info_book_label")
        self.author_label = builder.get_object("info_author_label")
        self.download_box = builder.get_object("info_download_box")
        self.download_label = builder.get_object("info_download_label")
        self.download_image = builder.get_object("info_download_image")
        self.download_switch = builder.get_object("info_download_switch")
        self.published_label = builder.get_object("info_published_label")
        self.last_played_label = builder.get_object("info_last_played_label")
        self.total_label = builder.get_object("info_total_label")
        self.remaining_label = builder.get_object("info_remaining_label")
        self.progress_bar = builder.get_object("book_progress_bar")
        self.cover_img = builder.get_object("info_cover_image")
        self.track_list_container = builder.get_object("track_list_container")
        self.published_text = builder.get_object("info_published_text")
        self.remaining_text = builder.get_object("info_remaining_text")
        self.play_book_button = builder.get_object("play_book_button")
        self.play_book_button.connect("clicked", self.__on_play_clicked)
        self.play_img = builder.get_object("play_img1")
        self.pause_img = builder.get_object("pause_img1")
        self.scroller = builder.get_object("book_overview_scroller")
        if Gtk.get_minor_version() > 20:
            self.scroller.props.propagate_natural_height = True

        self.ui.speed.add_listener(self.__ui_changed)
        player.add_player_listener(self.__player_changed)
        Settings().add_listener(self.__settings_changed)
        OfflineCache().add_listener(self.__on_offline_cache_changed)

    def set_book(self, book):
        """
        Display the given book in the book overview.
        """
        if self.book and self.book.id == book.id:
            self.update_time()
            return
        self.book = db.Book.get_by_id(book.id)

        if self.ui.is_playing and self.ui.titlebar.current_book and self.book.id == self.ui.titlebar.current_book.id:
            self.play_book_button.set_image(self.pause_img)
        else:
            self.play_book_button.set_image(self.play_img)

        self.name_label.set_text(book.name)
        self.author_label.set_text(book.author)

        self.update_offline_status()

        pixbuf = artwork_cache.get_cover_pixbuf(
            book, self.ui.window.get_scale_factor(), 250)
        if pixbuf:
            surface = Gdk.cairo_surface_create_from_pixbuf(
                pixbuf, self.ui.window.get_scale_factor(), None)
            self.cover_img.set_from_surface(surface)
        else:
            self.cover_img.set_from_icon_name("book-open-variant-symbolic", Gtk.IconSize.DIALOG)
            self.cover_img.props.pixel_size = 250

        self.duration = db.get_book_duration(book)
        self.speed = self.book.playback_speed
        self.total_label.set_text(
            tools.seconds_to_human_readable(self.duration / self.speed))

        self.last_played_label.set_text(
            tools.past_date_to_human_readable(book.last_played))

        self.published_label.set_visible(False)
        self.published_text.set_visible(False)

        # track list
        # This box contains all track content
        self.track_box = Gtk.Box()
        self.track_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.track_box.set_halign(Gtk.Align.START)
        self.track_box.set_valign(Gtk.Align.START)
        self.track_box.props.margin = 8

        disk_number = -1
        first_disk_element = None
        disk_count = 0

        for track in db.tracks(book):
            # Insert disk headers
            if track.disk != disk_number:
                disc_element = DiskElement(track.disk)
                self.track_box.add(disc_element)
                if disk_number == -1:
                    first_disk_element = disc_element
                    if track.disk < 2:
                        first_disk_element.set_hidden(True)
                else:
                    first_disk_element.show_all()
                    disc_element.show_all()

                disk_number = track.disk
                disk_count += 1

            track_element = TrackElement(track, self)
            self.track_box.add(track_element)
            track_element.show_all()

        tools.remove_all_children(self.track_list_container)
        self.track_box.show()
        self.track_box.set_halign(Gtk.Align.FILL)
        self.track_list_container.add(self.track_box)

        self._mark_current_track()
        self.update_time()

    def update_offline_status(self):
        """
        Hide/Show download elements depending on whether the book is on an external storage.
        """
        self.book = db.Book.get_by_id(self.book.id)
        if self.switch_signal:
            self.download_switch.disconnect(self.switch_signal)
        if db.is_external(self.book):
            self.download_box.set_visible(True)
            self.download_switch.set_visible(True)
            self.download_switch.set_active(self.book.offline)
        else:
            self.download_box.set_visible(False)
            self.download_switch.set_visible(False)
        self.switch_signal = self.download_switch.connect("notify::active", self.__on_download_switch_changed)

        self._set_book_download_status(self.book.downloaded)

    def update_time(self):
        if self.book is None:
            return

        # update book object
        # TODO: optimize usage by only asking from the db on track change
        self.book = db.Book.select().where(db.Book.id == self.book.id).get()
        if self.ui.titlebar.current_book and self.book.id == self.ui.titlebar.current_book.id:
            progress = db.get_book_progress(self.book, False)
            progress += (player.get_current_duration() / 1000000000)
            remaining = (self.duration - progress)
        else:
            progress = db.get_book_progress(self.book)
            remaining = db.get_book_remaining(self.book)
        percentage = progress / self.duration

        self.total_label.set_text(
            tools.seconds_to_human_readable(self.duration / self.speed))

        if percentage > 0.005:
            self.remaining_text.set_visible(True)
            self.remaining_label.set_visible(True)
            self.remaining_label.set_text(
                tools.seconds_to_human_readable(remaining / self.speed))
        else:
            self.remaining_text.set_visible(False)
            self.remaining_label.set_visible(False)

        self.progress_bar.set_fraction(percentage)

    def select_track(self, curr_track, playing):
        """
        Selects a track in the list and sets the play/pause icon.
        :param curr_track: Track to be selected
        :param playing: Display play (False) or pause (True) icon
        """
        if self.book is None or self.ui.titlebar.current_book.id != self.book.id:
            return

        self.deselect_track_element()

        if self.book.position == -1:
            return

        if curr_track:
            track_box_children = [e for e in self.track_box.get_children() if isinstance(e, TrackElement)]
            self.current_track_element = next(
                filter(
                    lambda x: x.track.id == curr_track.id,
                    track_box_children), None)

        if self.current_track_element is None:
            self.current_track_element = self.track_box.get_children()[0]

        self.current_track_element.select()
        self.current_track_element.set_playing(playing)

    def deselect_track_element(self):
        if self.current_track_element:
            self.current_track_element.set_playing(False)
            self.current_track_element.deselect()

    def block_ui_elements(self, block):
        """
        Blocks the download button. This gets called when a db scan is active.
        """
        self.download_switch.set_sensitive(not block)

    def _set_book_download_status(self, downloaded):
        if downloaded:
            self.download_image.set_from_icon_name("downloaded-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
            self.download_label.set_text(_("Downloaded"))
        else:
            self.download_image.set_from_icon_name("download-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
            self.download_label.set_text(_("Download"))

    def _mark_current_track(self):
        """
        Mark the current track position.
        """
        book = db.Book.select().where(db.Book.id == self.book.id).get()

        if book.position == -1:
            self.deselect_track_element()
            self.current_track_element = None
            return

        for track_element in self.track_box.get_children():
            if isinstance(track_element, DiskElement):
                continue
            elif track_element.track.id == book.position:
                self.current_track_element = track_element
                track_element.select()
            else:
                track_element.deselect()

        if book.position == 0:
            self.current_track_element = self.track_box.get_children()[1]
            self.current_track_element.select()

        if self.ui.titlebar.current_book and self.ui.titlebar.current_book.id == self.book.id:
            self.current_track_element.set_playing(self.ui.is_playing)

    def __ui_changed(self, event, message):
        """
        Handler for events that occur in the main ui.
        """
        if self.book is None or self.ui.titlebar.current_book is None or self.ui.titlebar.current_book.id != self.book.id:
            return

        if event == "playback-speed-changed":
            self.speed = db.Book.select().where(
                db.Book.id == self.book.id).get().playback_speed
            if self.ui.main_stack.props.visible_child_name == "book_overview":
                self.update_time()

    def __player_changed(self, event, message):
        """
        React to player changes.
        """
        if self.book is None or self.ui.titlebar.current_book is None or self.ui.titlebar.current_book.id != self.book.id:
            return

        if event == "play":
            self.play_book_button.set_image(self.pause_img)
            self.current_track_element.set_playing(True)
            self.last_played_label.set_text(
                tools.past_date_to_human_readable(message.book.last_played))
        elif event == "pause":
            self.play_book_button.set_image(self.play_img)
            self.current_track_element.set_playing(False)
        elif event == "stop":
            self._mark_current_track()
        elif event == "track-changed":
            track = player.get_current_track()
            self.select_track(track, self.ui.is_playing)

    def __settings_changed(self, event, message):
        """
        React to changes in user settings.
        """
        if not self.book:
            return

        if event == "storage-removed" or event == "external-storage-removed":
            if message in db.tracks(self.book).first().file:
                self.download_box.set_visible(False)
                self.download_switch.set_visible(False)
        elif "external-storage-added" or event == "storage-changed" or event == "storage-added":
            self.update_offline_status()

    def __on_play_clicked(self, event):
        """
        Play button clicked.
        Start/pause playback.
        """
        track = db.get_track_for_playback(self.book)
        current_track = player.get_current_track()

        if current_track and current_track.book.id == self.book.id:
            player.play_pause(None)
            if player.get_gst_player_state() == Gst.State.PLAYING:
                player.jump_to_ns(track.position)
        else:
            player.load_file(track)
            player.play_pause(None, True)

        return True

    def __on_download_switch_changed(self, switch, state):
        if self.download_switch.get_active():
            db.Book.update(offline=True).where(db.Book.id == self.book.id).execute()
            OfflineCache().add(self.book)
        else:
            db.Book.update(offline=False, downloaded=False).where(db.Book.id == self.book.id).execute()
            OfflineCache().remove(self.book)
            self._set_book_download_status(False)

    def __on_offline_cache_changed(self, event, message):
        """
        """
        if message is db.Book and message.id != self.book.id:
            return

        if event == "book-offline":
            self._set_book_download_status(True)
        elif event == "book-offline-removed":
            self._set_book_download_status(False)
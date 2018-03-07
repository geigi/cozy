from gi.repository import Gtk, Gdk

import cozy.artwork_cache as artwork_cache
import cozy.db as db
import cozy.tools as tools
import cozy.player as player

from cozy.book_element import TrackElement

class BookOverview:
    """
    This class contains all logic for the book overview.
    """
    book = None
    current_track_element = None

    def __init__(self, ui):
        self.ui = ui
        builder = ui.window_builder
        self.name_label = builder.get_object("info_book_label")
        self.author_label = builder.get_object("info_author_label")
        self.published_label = builder.get_object("info_published_label")
        self.last_played_label = builder.get_object("info_last_played_label")
        self.total_label = builder.get_object("info_total_label")
        self.remaining_label = builder.get_object("info_remaining_label")
        self.progress_bar = builder.get_object("book_progress_bar")
        self.cover_img = builder.get_object("info_cover_image")
        self.track_list_container = builder.get_object("track_list_container")
        self.published_text = builder.get_object("info_published_text")
        self.remaining_text = builder.get_object("info_remaining_text")

        self.ui.speed.add_listener(self.__ui_changed)
        player.add_player_listener(self.__player_changed)

    def set_book(self, book):
        if self.book is not None and self.book.id == book.id:
            self.update_time()
            return
        self.book = book

        self.name_label.set_text(book.name)
        self.author_label.set_text(book.author)

        pixbuf = artwork_cache.get_cover_pixbuf(book, self.ui.window.get_scale_factor(), 250)
        surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, self.ui.window.get_scale_factor(), None)
        self.cover_img.set_from_surface(surface)

        self.duration = db.get_book_duration(book)
        self.speed = db.Book.select().where(db.Book.id == self.book.id).get().playback_speed
        self.total_label.set_text(tools.seconds_to_human_readable(self.duration / self.speed))

        self.last_played_label.set_text(tools.past_date_to_human_readable(book.last_played))

        self.published_label.set_visible(False)
        self.published_text.set_visible(False)

        # track list
        # This box contains all track content
        self.track_box = Gtk.Box()
        self.track_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.track_box.set_halign(Gtk.Align.START)
        self.track_box.set_valign(Gtk.Align.START)
        self.track_box.props.margin = 8

        count = 0
        for track in db.tracks(book):
            self.track_box.add(TrackElement(track, self.ui, self))
            count += 1
        
        tools.remove_all_children(self.track_list_container)
        self.track_box.show_all()
        self.track_list_container.add(self.track_box)

        self._mark_current_track()
        self.update_time()
    
    def update_time(self):
        if self.book is None:
            return
        
        # update book object
        # TODO: optimize usage by only asking from the db on track change
        self.book = db.Book.select().where(db.Book.id == self.book.id).get()
        if self.ui.titlebar.current_book is not None and self.book.id == self.ui.titlebar.current_book.id:
            progress = db.get_book_progress(self.book, False)
            progress += (player.get_current_duration()  / 1000000000)
            remaining = (self.duration - progress)
        else:
            progress = db.get_book_progress(self.book)
            remaining = db.get_book_remaining(self.book)
        percentage = progress / self.duration

        self.total_label.set_text(tools.seconds_to_human_readable(self.duration / self.speed))

        if percentage > 0.005:
            self.remaining_text.set_visible(True)
            self.remaining_label.set_visible(True)
            self.remaining_label.set_text(tools.seconds_to_human_readable(remaining / self.speed))
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

        if curr_track is not None:
            self.current_track_element = next(
                filter(
                    lambda x: x.track.id == curr_track.id,
                    self.track_box.get_children()), None)

        if self.current_track_element is None:
            self.current_track_element = self.track_box.get_children()[0]

        self.current_track_element.select()
        self.current_track_element.set_playing(playing)

    def deselect_track_element(self):
        if self.current_track_element is not None:
            self.current_track_element.set_playing(False)
            self.current_track_element.deselect()

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
            if track_element.track.id == book.position:
                self.current_track_element = track_element
                track_element.select()
            else:
                track_element.deselect()

        if book.position == 0:
            self.current_track_element = self.track_box.get_children()[0]
            self.current_track_element.select()
        
        if self.ui.titlebar.current_book is not None and self.ui.titlebar.current_book.id == self.book.id:
            self.current_track_element.set_playing(self.ui.is_playing)
    
    def __ui_changed(self, event, message):
        """
        Handler for events that occur in the main ui.
        """
        if self.book is None or self.ui.titlebar.current_book.id != self.book.id:
            return
        
        if event == "playback-speed-changed":
            self.speed = db.Book.select().where(db.Book.id == self.book.id).get().playback_speed
            if self.ui.main_stack.props.visible_child_name == "book_overview":
                self.update_time()
    
    def __player_changed(self, event, message):
        """
        """
        if self.book is None or self.ui.titlebar.current_book is None or self.ui.titlebar.current_book.id != self.book.id:
            return

        if event == "play":
            self.current_track_element.set_playing(True)
        elif event == "pause":
            self.current_track_element.set_playing(False)
        elif event == "stop":
            self._mark_current_track()
        elif event == "track-changed":
            track = player.get_current_track()
            self.select_track(track, self.ui.is_playing)
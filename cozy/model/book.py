import logging
from typing import List

from peewee import SqliteDatabase, DoesNotExist

from cozy.application_settings import ApplicationSettings
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.architecture.profiler import timing
from cozy.db.collation import collate_natural
from cozy.db.book import Book as BookModel
from cozy.db.track import Track as TrackModel
from cozy.db.track_to_file import TrackToFile
from cozy.ext import inject
from cozy.model.chapter import Chapter
from cozy.model.settings import Settings
from cozy.model.track import Track, TrackInconsistentData

log = logging.getLogger("BookModel")


class BookIsEmpty(Exception):
    pass


class Book(Observable, EventSender):
    _chapters: List[Chapter] = None
    _settings: Settings = inject.attr(Settings)
    _app_settings: ApplicationSettings = inject.attr(ApplicationSettings)

    def __init__(self, db: SqliteDatabase, book: BookModel):
        super().__init__()
        super(Observable, self).__init__()

        self._db: SqliteDatabase = db
        self.id: int = book.id

        self._db_object: BookModel = book

        if TrackModel.select().where(TrackModel.book == self._db_object).count() < 1:
            raise BookIsEmpty

    @property
    def name(self):
        return self._db_object.name

    @name.setter
    def name(self, new_name: str):
        self._db_object.name = new_name
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def author(self):
        if not self._app_settings.swap_author_reader:
            return self._db_object.author
        else:
            return self._db_object.reader

    @author.setter
    def author(self, new_author: str):
        if not self._app_settings.swap_author_reader:
            self._db_object.author = new_author
        else:
            self._db_object.reader = new_author

        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def reader(self):
        if not self._app_settings.swap_author_reader:
            return self._db_object.reader
        else:
            return self._db_object.author

    @reader.setter
    def reader(self, new_reader: str):
        if not self._app_settings.swap_author_reader:
            self._db_object.reader = new_reader
        else:
            self._db_object.author = new_reader

        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def position(self) -> int:
        return self._db_object.position

    @position.setter
    def position(self, new_position: int):
        self._db_object.position = new_position
        self._db_object.save(only=self._db_object.dirty_fields)
        self._notify("position")
        self._notify("current_chapter")

    @property
    def rating(self):
        return self._db_object.rating

    @rating.setter
    def rating(self, new_rating: int):
        self._db_object.rating = new_rating
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def cover(self):
        return self._db_object.cover

    @cover.setter
    def cover(self, new_cover: bytes):
        self._db_object.cover = new_cover
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def playback_speed(self):
        return self._db_object.playback_speed

    @playback_speed.setter
    def playback_speed(self, new_playback_speed: float):
        self._db_object.playback_speed = new_playback_speed
        self._db_object.save(only=self._db_object.dirty_fields)
        self._notify("playback_speed")

    @property
    def last_played(self):
        return self._db_object.last_played

    @last_played.setter
    def last_played(self, new_last_played: int):
        self._db_object.last_played = new_last_played
        self._db_object.save(only=self._db_object.dirty_fields)
        self._notify("last_played")

    @property
    def offline(self):
        return self._db_object.offline

    @offline.setter
    def offline(self, new_offline: bool):
        self._db_object.offline = new_offline
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def downloaded(self):
        return self._db_object.downloaded

    @downloaded.setter
    def downloaded(self, new_downloaded: bool):
        self._db_object.downloaded = new_downloaded
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def chapters(self):
        if not self._chapters:
            self._fetch_chapters()

        return self._chapters

    @property
    def current_chapter(self):
        return next((chapter for chapter in self.chapters if chapter.id == self.position), self.chapters[0])

    @property
    def duration(self):
        return sum((chapter.length for chapter in self.chapters))

    @property
    def progress(self):
        progress = 0

        if self.position == 0:
            return 0
        elif self.position == -1:
            return self.duration

        for chapter in self.chapters:
            if chapter.id == self.position:
                relative_position = max(chapter.position - chapter.start_position, 0)
                progress += int(relative_position / 1000000000)
                return progress

            progress += chapter.length

        return progress

    def remove(self):
        if self._settings.last_played_book and self._settings.last_played_book.id == self._db_object.id:
            self._settings.last_played_book = None

        book_tracks = [TrackModel.get_by_id(chapter.id) for chapter in self.chapters]
        track_to_files = TrackToFile.select().join(TrackModel).where(TrackToFile.track << book_tracks)

        for track in track_to_files:
            try:
                track.file.delete_instance(recursive=True)
            except DoesNotExist:
                track.delete_instance()

        for track in book_tracks:
            track.delete_instance(recursive=True)

        self._db_object.delete_instance(recursive=True)
        self.destroy_listeners()
        self._destroy_observers()

    def _fetch_chapters(self):
        tracks = TrackModel \
            .select() \
            .where(TrackModel.book == self._db_object) \
            .order_by(TrackModel.disk, TrackModel.number, collate_natural.collation(TrackModel.name))

        self._chapters = []
        for track in tracks:
            try:
                track_model = Track(self._db, track)
                self._chapters.append(track_model)
            except TrackInconsistentData:
                log.warning("Skipping inconsistent model")
            except Exception as e:
                log.error("Could not create chapter object: {}".format(e))

        for chapter in self._chapters:
            chapter.add_listener(self._on_chapter_event)

    def _on_chapter_event(self, event: str, chapter: Chapter):
        if event == "chapter-deleted":
            try:
                self.chapters.remove(chapter)
            except ValueError:
                pass

            if len(self._chapters) < 1:
                if self._settings.last_played_book and self._settings.last_played_book.id == self._db_object.id:
                    self._settings.last_played_book = None

                self._db_object.delete_instance(recursive=True)
                self.emit_event("book-deleted", self)
                self.destroy_listeners()
                self._destroy_observers()

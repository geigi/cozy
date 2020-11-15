from typing import List

from peewee import SqliteDatabase

from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.db.book import Book as BookModel
from cozy.db.storage_blacklist import StorageBlackList
from cozy.db.track import Track as TrackModel
from cozy.ext import inject
from cozy.model.chapter import Chapter
from cozy.model.settings import Settings
from cozy.model.track import Track


class BookIsEmpty(Exception):
    pass


class Book(Observable, EventSender):
    _chapters: List[Chapter] = None
    _settings: Settings = inject.attr(Settings)

    def __init__(self, db: SqliteDatabase, id: int):
        super().__init__()
        super(Observable, self).__init__()

        self._db: SqliteDatabase = db
        self.id: int = id

        self._get_db_object()

    def _get_db_object(self):
        self._db_object: BookModel = BookModel.get(self.id)

        if TrackModel.select().where(TrackModel.book == self._db_object).count() < 1:
            raise BookIsEmpty

    # This property is for the transition time only
    # Because everything is hardwired to the database objects
    # Step by step, you got this...
    @property
    def db_object(self):
        return self._db_object

    @property
    def name(self):
        return self._db_object.name

    @name.setter
    def name(self, new_name: str):
        self._db_object.name = new_name
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def author(self):
        return self._db_object.author

    @author.setter
    def author(self, new_author: str):
        self._db_object.author = new_author
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def reader(self):
        return self._db_object.reader

    @reader.setter
    def reader(self, new_reader: str):
        self._db_object.reader = new_reader
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
        self._notify("duration")
        self._notify("progress")

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
        return sum((chapter.length for chapter in self.chapters)) / self.playback_speed

    @property
    def progress(self):
        progress = 0

        if self.position == 0:
            return 0
        elif self.position == -1:
            return self.duration

        for chapter in self.chapters:
            if chapter.id == self.position:
                progress += int(chapter.position / 1000000000)
                return progress / self.playback_speed

            progress += chapter.length

        return progress / self.playback_speed

    def reload(self):
        self._get_db_object()

    def remove(self):
        if self._settings.last_played_book and self._settings.last_played_book.id == self._db_object.id:
            self._settings.last_played_book = None

        book_tracks = [TrackModel.get_by_id(chapter.id) for chapter in self.chapters]
        data = list((t.file,) for t in book_tracks)
        chunks = [data[x:x + 500] for x in range(0, len(data), 500)]
        for chunk in chunks:
            StorageBlackList.insert_many(chunk, fields=[StorageBlackList.path]).execute()
        ids = list(t.id for t in book_tracks)
        TrackModel.delete().where(TrackModel.id << ids).execute()
        self._db_object.delete_instance(recursive=True)
        self.destroy_listeners()
        self._destroy_observers()

    def _fetch_chapters(self):
        tracks = TrackModel \
            .select(TrackModel.id) \
            .where(TrackModel.book == self._db_object) \
            .order_by(TrackModel.disk, TrackModel.number, TrackModel.name)
        self._chapters = [Track(self._db, track.id) for track in tracks]

        for chapter in self._chapters:
            chapter.add_listener(self._on_chapter_event)

    def _on_chapter_event(self, event: str, chapter: Chapter):
        if event == "chapter-deleted":
            self._chapters.remove(chapter)

            if len(self._chapters) < 1:
                if self._settings.last_played_book and self._settings.last_played_book.id == self._db_object.id:
                    self._settings.last_played_book = None

                self._db_object.delete_instance(recursive=True)
                self.emit_event("book-deleted", self)
                self.destroy_listeners()
                self._destroy_observers()

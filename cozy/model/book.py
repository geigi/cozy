from typing import List

from peewee import SqliteDatabase

from cozy.architecture.event_sender import EventSender
from cozy.db.book import Book as BookModel
from cozy.db.storage_blacklist import StorageBlackList
from cozy.db.track import Track as TrackModel
from cozy.model.chapter import Chapter
from cozy.model.track import Track


class BookIsEmpty(Exception):
    pass


class Book(EventSender):
    _chapters: List[Chapter] = None

    def __init__(self, db: SqliteDatabase, id: int):
        super().__init__()
        self._db: SqliteDatabase = db
        self.id: int = id

        self._get_db_object()

    def _get_db_object(self):
        with self._db:
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
        with self._db:
            self._db_object.name = new_name
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def author(self):
        return self._db_object.author

    @author.setter
    def author(self, new_author: str):
        with self._db:
            self._db_object.author = new_author
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def reader(self):
        return self._db_object.reader

    @reader.setter
    def reader(self, new_reader: str):
        with self._db:
            self._db_object.reader = new_reader
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def position(self):
        return self._db_object.position

    @position.setter
    def position(self, new_position: int):
        with self._db:
            self._db_object.position = new_position
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def rating(self):
        return self._db_object.rating

    @rating.setter
    def rating(self, new_rating: int):
        with self._db:
            self._db_object.rating = new_rating
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def cover(self):
        return self._db_object.cover

    @cover.setter
    def cover(self, new_cover: bytes):
        with self._db:
            self._db_object.cover = new_cover
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def playback_speed(self):
        return self._db_object.playback_speed

    @playback_speed.setter
    def playback_speed(self, new_playback_speed: float):
        with self._db:
            self._db_object.playback_speed = new_playback_speed
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def last_played(self):
        return self._db_object.last_played

    @last_played.setter
    def last_played(self, new_last_played: int):
        with self._db:
            self._db_object.last_played = new_last_played
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def offline(self):
        return self._db_object.offline

    @offline.setter
    def offline(self, new_offline: bool):
        with self._db:
            self._db_object.offline = new_offline
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def downloaded(self):
        return self._db_object.downloaded

    @downloaded.setter
    def downloaded(self, new_downloaded: bool):
        with self._db:
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

    def reload(self):
        self._get_db_object()

    def blacklist(self):
        with self._db:
            book_tracks = [TrackModel.get_by_id(chapter.id) for chapter in self._chapters]
            data = list((t.file,) for t in book_tracks)
            chunks = [data[x:x + 500] for x in range(0, len(data), 500)]
            for chunk in chunks:
                StorageBlackList.insert_many(chunk, fields=[StorageBlackList.path]).execute()
            ids = list(t.id for t in book_tracks)
            TrackModel.delete().where(TrackModel.id << ids).execute()
            self._db_object.delete_instance()

    def _fetch_chapters(self):
        with self._db:
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
                with self._db:
                    self._db_object.delete().execute()
                self.emit_event("book-deleted", self)
                self.destroy()

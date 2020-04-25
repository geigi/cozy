from peewee import SqliteDatabase
from cozy.db.book import Book as BookModel


class Book:
    def __init__(self, db: SqliteDatabase, id: int):
        self.db: SqliteDatabase = db
        self.id: int = id

        with self.db:
            self.db_object: BookModel = BookModel.get(self.id)

    @property
    def name(self):
        return self.db_object.name

    @name.setter
    def name(self, new_name: str):
        with self.db:
            self.db_object.name = new_name
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def author(self):
        return self.db_object.author

    @author.setter
    def author(self, new_author: str):
        with self.db:
            self.db_object.author = new_author
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def reader(self):
        return self.db_object.reader

    @reader.setter
    def reader(self, new_reader: str):
        with self.db:
            self.db_object.reader = new_reader
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def position(self):
        return self.db_object.position

    @position.setter
    def position(self, new_position: int):
        with self.db:
            self.db_object.position = new_position
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def rating(self):
        return self.db_object.rating

    @rating.setter
    def rating(self, new_rating: int):
        with self.db:
            self.db_object.rating = new_rating
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def cover(self):
        return self.db_object.cover

    @cover.setter
    def cover(self, new_cover: bytes):
        with self.db:
            self.db_object.cover = new_cover
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def playback_speed(self):
        return self.db_object.playback_speed

    @playback_speed.setter
    def playback_speed(self, new_playback_speed: float):
        with self.db:
            self.db_object.playback_speed = new_playback_speed
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def last_played(self):
        return self.db_object.last_played

    @last_played.setter
    def last_played(self, new_last_played: int):
        with self.db:
            self.db_object.last_played = new_last_played
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def offline(self):
        return self.db_object.offline

    @offline.setter
    def offline(self, new_offline: bool):
        with self.db:
            self.db_object.offline = new_offline
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def downloaded(self):
        return self.db_object.downloaded

    @downloaded.setter
    def downloaded(self, new_downloaded: bool):
        with self.db:
            self.db_object.downloaded = new_downloaded
            self.db_object.save(only=self.db_object.dirty_fields)
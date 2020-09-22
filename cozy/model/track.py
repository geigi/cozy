from peewee import SqliteDatabase

from cozy.db.track import Track as TrackModel
from cozy.model.chapter import Chapter


class Track(Chapter):
    def __init__(self, db: SqliteDatabase, id: int):
        super().__init__()
        self._db: SqliteDatabase = db
        self.id: int = id

        with self._db:
            self._db_object: TrackModel = TrackModel.get(self.id)

    @property
    def name(self):
        return self._db_object.name

    @name.setter
    def name(self, new_name: str):
        with self._db:
            self._db_object.name = new_name
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def number(self):
        return self._db_object.number

    @number.setter
    def number(self, new_number: int):
        with self._db:
            self._db_object.number = new_number
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def disk(self):
        return self._db_object.disk

    @disk.setter
    def disk(self, new_disk: int):
        with self._db:
            self._db_object.disk = new_disk
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
    def file(self):
        return self._db_object.file

    @file.setter
    def file(self, new_file: str):
        with self._db:
            self._db_object.file = new_file
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def length(self):
        return self._db_object.length

    @length.setter
    def length(self, new_length: float):
        with self._db:
            self._db_object.length = new_length
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def modified(self):
        return self._db_object.modified

    @modified.setter
    def modified(self, new_modified: int):
        with self._db:
            self._db_object.modified = new_modified
            self._db_object.save(only=self._db_object.dirty_fields)

    def delete(self):
        with self._db:
            self._db_object.delete_instance(recursive=True)
            self.emit_event("chapter-deleted", self)
            self.destroy()

from peewee import SqliteDatabase

from cozy.db.track import Track as TrackModel
from cozy.model.chapter import Chapter

NS_TO_SEC = 10 ** 9


class Track(Chapter):
    def __init__(self, db: SqliteDatabase, id: int):
        super().__init__()
        self._db: SqliteDatabase = db
        self.id: int = id

        self._db_object: TrackModel = TrackModel.get(self.id)

    @property
    def name(self):
        return self._db_object.name

    @name.setter
    def name(self, new_name: str):
        self._db_object.name = new_name
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def number(self):
        return self._db_object.number

    @number.setter
    def number(self, new_number: int):
        self._db_object.number = new_number
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def disk(self):
        return self._db_object.disk

    @disk.setter
    def disk(self, new_disk: int):
        self._db_object.disk = new_disk
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def position(self):
        return self._db_object.position

    @position.setter
    def position(self, new_position: int):
        self._db_object.position = new_position
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def start_position(self) -> int:
        return 0

    @property
    def end_position(self) -> int:
        return int(self.length) * NS_TO_SEC

    @property
    def file(self):
        return self._db_object.file

    @file.setter
    def file(self, new_file: str):
        self._db_object.file = new_file
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def length(self) -> float:
        return self._db_object.length

    @length.setter
    def length(self, new_length: float):
        self._db_object.length = new_length
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def modified(self):
        return self._db_object.modified

    @modified.setter
    def modified(self, new_modified: int):
        self._db_object.modified = new_modified
        self._db_object.save(only=self._db_object.dirty_fields)

    def delete(self):
        self._db_object.delete_instance(recursive=True)
        self.emit_event("chapter-deleted", self)
        self.destroy_listeners()

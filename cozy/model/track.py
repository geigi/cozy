from peewee import SqliteDatabase

from cozy.db.track import Track as TrackModel


class Track:
    def __init__(self, db: SqliteDatabase, id: int):
        self.db: SqliteDatabase = db
        self.id: int = id

        with self.db:
            self.db_object: TrackModel = TrackModel.get(self.id)

    @property
    def name(self):
        return self.db_object.name

    @name.setter
    def name(self, new_name: str):
        with self.db:
            self.db_object.name = new_name
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def number(self):
        return self.db_object.number

    @number.setter
    def number(self, new_number: int):
        with self.db:
            self.db_object.number = new_number
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def disk(self):
        return self.db_object.disk

    @disk.setter
    def disk(self, new_disk: int):
        with self.db:
            self.db_object.disk = new_disk
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
    def file(self):
        return self.db_object.file

    @file.setter
    def file(self, new_file: str):
        with self.db:
            self.db_object.file = new_file
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def length(self):
        return self.db_object.length

    @length.setter
    def length(self, new_length: float):
        with self.db:
            self.db_object.length = new_length
            self.db_object.save(only=self.db_object.dirty_fields)

    @property
    def modified(self):
        return self.db_object.modified

    @modified.setter
    def modified(self, new_modified: int):
        with self.db:
            self.db_object.modified = new_modified
            self.db_object.save(only=self.db_object.dirty_fields)

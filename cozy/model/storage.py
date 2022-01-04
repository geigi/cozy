import os

from peewee import SqliteDatabase

from cozy.db.storage import Storage as StorageModel


class InvalidPath(Exception):
    pass


class Storage:
    def __init__(self, db: SqliteDatabase, db_id: int):
        self._db: SqliteDatabase = db
        self.id: int = db_id

        self._get_db_object()

    @staticmethod
    def new(db: SqliteDatabase):
        db_obj = StorageModel.create(path="")
        return Storage(db, db_obj.id)

    def _get_db_object(self):
        self._db_object: StorageModel = StorageModel.get(self.id)

    @property
    def db_object(self):
        return self._db_object

    @property
    def path(self):
        return self._db_object.path

    @path.setter
    def path(self, new_path: str):
        if not os.path.isabs(new_path):
            raise InvalidPath

        self._db_object.path = new_path
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def location_type(self):
        return self._db_object.location_type

    @location_type.setter
    def location_type(self, new_location_type: int):
        self._db_object.location_type = new_location_type
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def default(self):
        return self._db_object.default

    @default.setter
    def default(self, new_default: bool):
        self._db_object.default = new_default
        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def external(self):
        return self._db_object.external

    @external.setter
    def external(self, new_external: bool):
        self._db_object.external = new_external
        self._db_object.save(only=self._db_object.dirty_fields)

    def delete(self):
        self._db_object.delete_instance(recursive=True, delete_nullable=False)
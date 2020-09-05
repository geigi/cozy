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

    def _get_db_object(self):
        with self._db:
            self._db_object: StorageModel = StorageModel.get(self.id)

    @property
    def path(self):
        return self._db_object.path

    @path.setter
    def path(self, new_path: str):
        if not os.path.isabs(new_path):
            raise InvalidPath

        with self._db:
            self._db_object.path = new_path
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def location_type(self):
        return self._db_object.location_type

    @location_type.setter
    def location_type(self, new_location_type: int):
        with self._db:
            self._db_object.location_type = new_location_type
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def default(self):
        return self._db_object.default

    @default.setter
    def default(self, new_default: bool):
        with self._db:
            self._db_object.default = new_default
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def external(self):
        return self._db_object.external

    @external.setter
    def external(self, new_external: bool):
        with self._db:
            self._db_object.external = new_external
            self._db_object.save(only=self._db_object.dirty_fields)

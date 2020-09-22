import logging
from typing import List

import cozy.ext.inject as inject
from peewee import SqliteDatabase

from cozy.db.book import Book
from cozy.db.settings import Settings as SettingsModel
from cozy.db.storage import Storage as StorageModel
from cozy.model.storage import Storage, InvalidPath

log = logging.getLogger("model.storage_location")


class Settings:
    _storages: List[Storage] = []
    _db = cache = inject.attr(SqliteDatabase)

    def __init__(self):
        with self._db:
            self._db_object: SettingsModel = SettingsModel.get()

    @property
    def first_start(self) -> bool:
        return self._db_object.first_start

    @property
    def last_played_book(self) -> Book:
        return self._db_object.last_played_book

    @last_played_book.setter
    def last_played_book(self, new_value: Book):
        with self._db:
            self._db_object.last_played_book = new_value
            self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def storage_locations(self):
        if not self._storages:
            self._load_all_storage_locations()

        return self._storages

    @property
    def external_storage_locations(self):
        if not self._storages:
            self._load_all_storage_locations()

        return [storage for storage in self._storages if storage.external]

    def invalidate(self):
        self._storages = []

    def _load_all_storage_locations(self):
        with self._db:
            for storage_db_obj in StorageModel.select(StorageModel.id):
                try:
                    self._storages.append(Storage(self._db, storage_db_obj.id))
                except InvalidPath:
                    log.error("Invalid path found in database, skipping: {}".format(storage_db_obj.path))

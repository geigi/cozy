import logging
from typing import List, Optional

import peewee

import cozy.ext.inject as inject
from peewee import SqliteDatabase

from cozy.db.book import Book
from cozy.db.settings import Settings as SettingsModel
from cozy.db.storage import Storage as StorageModel
from cozy.model.storage import Storage, InvalidPath
from cozy.report import reporter

log = logging.getLogger("model.storage_location")


class Settings:
    _storages: list[Storage] = []
    _db = cache = inject.attr(SqliteDatabase)

    def __init__(self):
        self._db_object: SettingsModel = SettingsModel.get()

    @property
    def first_start(self) -> bool:
        return self._db_object.first_start

    @property
    def last_played_book(self) -> Optional[Book]:
        try:
            return self._db_object.last_played_book
        except peewee.DoesNotExist:
            log.warning("last_played_book references an non existent object. Setting last_played_book to None.")
            reporter.warning("settings_model",
                             "last_played_book references an non existent object. Setting last_played_book to None.")

            self.last_played_book = None
            return None

    @last_played_book.setter
    def last_played_book(self, new_value):
        if new_value:
            self._db_object.last_played_book = new_value._db_object
        else:
            self._db_object.last_played_book = None

        self._db_object.save(only=self._db_object.dirty_fields)

    @property
    def default_location(self):
        return next(location for location in self.storage_locations if location.default)

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
        self._storages.clear()

    def _load_all_storage_locations(self):
        for storage_db_obj in StorageModel.select(StorageModel.id):
            try:
                self._storages.append(Storage(self._db, storage_db_obj.id))
            except InvalidPath:
                log.error("Invalid path found in database, skipping: {}".format(storage_db_obj.path))

        self._ensure_default_storage_present()

    def _ensure_default_storage_present(self):
        if self._storages and not any(storage.default for storage in self._storages):
            self._storages[0].default = True

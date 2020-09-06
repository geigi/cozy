import logging
from typing import List

import cozy.ext.inject as inject
from peewee import SqliteDatabase

from cozy.db.storage import Storage as StorageModel
from cozy.model.storage import Storage, InvalidPath

log = logging.getLogger("model.storage_location")


class Settings:
    _storages: List[Storage] = []
    _db = cache = inject.attr(SqliteDatabase)

    @property
    def storage_locations(self):
        if not self._storages:
            self._load_all_storage_locations()

        return self._storages

    def invalidate(self):
        self._storages = []

    def _load_all_storage_locations(self):
        with self._db:
            for storage_db_obj in StorageModel.select(StorageModel.id):
                try:
                    self._storages.append(Storage(self._db, storage_db_obj.id))
                except InvalidPath:
                    log.error("Invalid path found in database, skipping: {}".format(storage_db_obj.path))

from peewee import SqliteDatabase

from cozy.db.storage_blacklist import StorageBlackList
from cozy.ext import inject


class StorageBlockList:
    _db = cache = inject.attr(SqliteDatabase)

    def rebase_path(self, old_path: str, new_path: str):
        for element in StorageBlackList.select():
            if old_path in element.path:
                new_file_path = element.path.replace(old_path, new_path)
                StorageBlackList.update(path=new_file_path).where(StorageBlackList.id == element.id).execute()

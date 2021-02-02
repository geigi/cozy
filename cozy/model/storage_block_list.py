from peewee import SqliteDatabase

from cozy.db.storage_blacklist import StorageBlackList
from cozy.db.track import Track as TrackModel
from cozy.ext import inject
from cozy.model.book import Book


class StorageBlockList:
    _db = cache = inject.attr(SqliteDatabase)

    def rebase_path(self, old_path: str, new_path: str):
        for element in StorageBlackList.select():
            if old_path in element.path:
                new_file_path = element.path.replace(old_path, new_path)
                StorageBlackList.update(path=new_file_path).where(StorageBlackList.id == element.id).execute()

    def add_book(self, book: Book):
        book_tracks = [TrackModel.get_by_id(chapter.id) for chapter in book.chapters]

        data = list((t.file,) for t in book_tracks)
        chunks = [data[x:x + 500] for x in range(0, len(data), 500)]
        for chunk in chunks:
            StorageBlackList.insert_many(chunk, fields=[StorageBlackList.path]).execute()

from typing import List, Set

from peewee import SqliteDatabase

from cozy.db.book import Book as BookModel
from cozy.db.track import Track
from cozy.ext import inject
from cozy.extensions.set import split_strings_to_set
from cozy.media.media_file import MediaFile

from cozy.model.book import Book, BookIsEmpty
from cozy.model.chapter import Chapter


class Library:
    _db = cache = inject.attr(SqliteDatabase)

    _books: List[Book] = []
    _chapters: Set[Chapter] = set()
    _files: Set[str] = set()

    @property
    def authors(self):
        authors = {book.author for book in self.books}
        authors = split_strings_to_set(authors)
        return authors

    @property
    def readers(self):
        readers = {book.reader for book in self.books}
        readers = split_strings_to_set(readers)
        return readers

    @property
    def books(self):
        if not self._books:
            self._load_all_books()

        return self._books

    @property
    def chapters(self) -> Set[Chapter]:
        if not self._chapters:
            self._load_all_chapters()

        return self._chapters

    @property
    def files(self) -> Set[str]:
        if not self._files:
            self._load_all_files()

        return self._files

    def invalidate(self):
        self._books = []
        self._chapters = set()
        self._files = set()

    def insert_many(self, media_files: List[MediaFile]):
        tracks = self._prepare_db_objects(media_files)

        with self._db:
            Track.insert_many(tracks).execute()

    def _prepare_db_objects(self, media_files: List[MediaFile]) -> List[object]:
        for media_file in media_files:
            if not media_file:
                continue

            with self._db:
                book = self._import_or_update_book(media_file)

                if len(media_file.chapters) == 1:
                    track = self._get_track_dictionary_for_db(media_file, book)
                else:
                    raise NotImplemented

                if media_file.path not in self.files:
                    yield track
                else:
                    self._update_track_db_object(book, media_file)

    def _import_or_update_book(self, media_file):
        if BookModel.select(BookModel.name).where(BookModel.name == media_file.book_name).count() < 1:
            book = self._create_book_db_object(media_file)
        else:
            book = self._update_book_db_object(media_file)
        return book

    def _get_track_dictionary_for_db(self, media_file, book):
        return {
            "name": media_file.chapters[0].name,
            "number": media_file.track_number,
            "disk": media_file.disk,
            "book": book,
            "file": media_file.path,
            "length": media_file.length,
            "modified": media_file.modified,
            "position": media_file.chapters[0].position
        }

    def _update_track_db_object(self, book: BookModel, media_file: MediaFile):
        Track.update(name=media_file.track_number,
                     number=media_file.track_number,
                     book=book,
                     disk=media_file.disk,
                     length=media_file.length,
                     modified=media_file.modified) \
            .where(Track.file == media_file.path) \
            .execute()

    def _update_book_db_object(self, media_file: MediaFile) -> BookModel:
        BookModel.update(name=media_file.book_name,
                         author=media_file.author,
                         reader=media_file.reader,
                         cover=media_file.cover) \
            .where(BookModel.name == media_file.book_name) \
            .execute()
        return BookModel.select().where(BookModel.name == media_file.book_name).get()

    def _create_book_db_object(self, media_file: MediaFile) -> BookModel:
        return BookModel.create(name=media_file.book_name,
                                author=media_file.author,
                                reader=media_file.reader,
                                cover=media_file.cover,
                                position=0,
                                rating=-1)

    def _load_all_books(self):
        with self._db:
            for book_db_obj in BookModel.select(BookModel.id):
                try:
                    self._books.append(Book(self._db, book_db_obj.id))
                except BookIsEmpty:
                    pass

    def _load_all_chapters(self):
        self._chapters = {chapter
                          for book_chapters
                          in [book.chapters for book in self.books]
                          for chapter
                          in book_chapters}

    def _load_all_files(self):
        self._files = {chapter.file
                       for chapter
                       in self.chapters}

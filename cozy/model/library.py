from typing import List

from peewee import SqliteDatabase

from cozy.db.book import Book as BookModel

from cozy.model.book import Book, BookIsEmpty


class Library:
    _books: List[Book] = []

    def __init__(self, db: SqliteDatabase):
        self._db = db

    @property
    def authors(self):
        return {book.author for book in self.books}

    @property
    def readers(self):
        return {book.reader for book in self.books}

    @property
    def books(self):
        if not self._books:
            self._load_all_books()

        return self._books

    def invalidate(self):
        self._books = []

    def _load_all_books(self):
        with self._db:
            for book_db_obj in BookModel.select(BookModel.id):
                try:
                    self._books.append(Book(self._db, book_db_obj.id))
                except BookIsEmpty:
                    pass

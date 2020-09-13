from typing import List

from peewee import SqliteDatabase

from cozy.db.book import Book as BookModel
from cozy.extensions.set import split_strings_to_set

from cozy.model.book import Book, BookIsEmpty


class Library:
    _books: List[Book] = []

    def __init__(self, db):
        self._db: SqliteDatabase = db

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
    def chapters(self):
        if not self._books:
            self._load_all_books()

        return [chapter for book_chapters in [book.chapters for book in self._books] for chapter in book_chapters]

    def invalidate(self):
        self._books = []

    def _load_all_books(self):
        with self._db:
            for book_db_obj in BookModel.select(BookModel.id):
                try:
                    self._books.append(Book(self._db, book_db_obj.id))
                except BookIsEmpty:
                    pass

import logging
from typing import List, Set, Optional

from peewee import SqliteDatabase

from cozy.architecture.event_sender import EventSender
from cozy.architecture.profiler import timing
from cozy.db.book import Book as BookModel
from cozy.ext import inject
from cozy.extensions.set import split_strings_to_set
from cozy.model.book import Book, BookIsEmpty
from cozy.model.chapter import Chapter
from cozy.model.database_importer import DatabaseImporter
from cozy.model.settings import Settings

log = logging.getLogger("ui")


class Library(EventSender):
    _db = cache = inject.attr(SqliteDatabase)
    _settings: Settings = inject.attr(Settings)
    _database_importer: DatabaseImporter = inject.attr(DatabaseImporter)

    _books: List[Book] = []
    _chapters: Set[Chapter] = set()
    _files: Set[str] = set()

    def __init__(self):
        super().__init__()

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

    @property
    def last_played_book(self) -> Optional[Book]:
        if not self._settings.last_played_book:
            return None

        last_book = next((book
                          for book
                          in self.books
                          if book.id == self._settings.last_played_book.id), None)

        return last_book

    @last_played_book.setter
    def last_played_book(self, new_value: Optional[Book]):
        self._settings.last_played_book = new_value

    def invalidate(self):
        for book in self._books:
            book.destroy_listeners()

        self._books = []

        for chapter in self._chapters:
            chapter.destroy_listeners()

        self._chapters = set()
        self._files = set()

    @timing
    def rebase_path(self, old_path: str, new_path: str):
        self.emit_event_main_thread("rebase-started")

        chapter_count = len(self.chapters)
        progress = 0
        for chapter in self.chapters:
            if chapter.file.startswith(old_path):
                progress += 1
                chapter.file = chapter.file.replace(old_path, new_path)
                self.emit_event_main_thread("rebase-progress", progress / chapter_count)

        self.emit_event_main_thread("rebase-finished")

    def _load_all_books(self):
        for book_db_obj in BookModel.select(BookModel.id):
            try:
                book = Book(self._db, book_db_obj.id)
                book.add_listener(self._on_book_event)
                self._books.append(book)
            except BookIsEmpty:
                pass

    def _load_all_chapters(self):
        self._chapters = {chapter
                          for book_chapters
                          in [book.chapters for book in self.books]
                          for chapter
                          in book_chapters}

        for chapter in self._chapters:
            chapter.add_listener(self._on_chapter_event)

    def _load_all_files(self):
        self._files = {chapter.file
                       for chapter
                       in self.chapters}

    def _on_chapter_event(self, event: str, chapter: Chapter):
        if event == "chapter-deleted":
            try:
                self.chapters.remove(chapter)
            except KeyError:
                log.error("Could not remove chapter from library chapter list.")

            try:
                self.files.remove(chapter.file)
            except KeyError:
                log.error("Could not remove file from library file list.")
                self._files = []

    def _on_book_event(self, event: str, book):
        if event == "book-deleted":
            self.books.remove(book)

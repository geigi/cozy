import logging
from typing import List, Set, Optional

from peewee import SqliteDatabase

from cozy.architecture.event_sender import EventSender
from cozy.architecture.profiler import timing
from cozy.db.book import Book as BookModel
from cozy.db.track import Track
from cozy.ext import inject
from cozy.extensions.set import split_strings_to_set
from cozy.media.media_file import MediaFile

from cozy.model.book import Book, BookIsEmpty
from cozy.model.chapter import Chapter
from cozy.model.settings import Settings

log = logging.getLogger("ui")


class Library(EventSender):
    _db = cache = inject.attr(SqliteDatabase)
    _settings: Settings = inject.attr(Settings)

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

    def insert_many(self, media_files: Set[MediaFile]):
        tracks = self._prepare_db_objects(media_files)

        Track.insert_many(tracks).execute()

    def _prepare_db_objects(self, media_files: Set[MediaFile]) -> Set[object]:
        book_db_objects: Set[BookModel] = set()

        for media_file in media_files:
            if not media_file:
                continue

            book = next((book for book in book_db_objects if book.name == media_file.book_name), None)

            if not book:
                book = self._import_or_update_book(media_file)
                book_db_objects.add(book)

            if len(media_file.chapters) == 1:
                track = self._get_track_dictionary_for_db(media_file, book)
            else:
                raise NotImplementedError

            if media_file.path not in self.files:
                yield track
            else:
                self._update_track_db_object(media_file, book)

    def _import_or_update_book(self, media_file):
        if BookModel.select(BookModel.name).where(BookModel.name == media_file.book_name).count() < 1:
            book = self._create_book_db_object(media_file)
        else:
            book = self._update_book_db_object(media_file)
        return book

    def _get_track_dictionary_for_db(self, media_file: MediaFile, book: BookModel):
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

    def _update_track_db_object(self, media_file: MediaFile, book: BookModel):
        Track.update(name=media_file.chapters[0].name,
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

from test.cozy.mocks import ApplicationSettingsMock

import inject
import pytest
from peewee import SqliteDatabase

from cozy.application_settings import ApplicationSettings
from cozy.model.settings import Settings


@pytest.fixture(autouse=True)
def setup_inject(peewee_database):
    inject.clear()
    inject.configure(lambda binder: (binder.bind(SqliteDatabase, peewee_database),
                                     binder.bind_to_constructor(Settings, lambda: Settings())
                                     .bind_to_constructor(ApplicationSettings, lambda: ApplicationSettingsMock())))
    yield
    inject.clear()


def test_library_contains_books():
    from cozy.model.library import Library

    library = Library()

    assert len(library.books) > 0


def test_authors_contains_every_author_from_db():
    from cozy.model.library import Library, split_strings_to_set
    from cozy.db.book import Book

    library = Library()
    books = Book.select(Book.author).distinct().order_by(Book.author)
    authors_from_db = [book.author for book in books]
    authors_from_db = list(split_strings_to_set(set(authors_from_db)))

    # we cannot assert the same content as the library filters books without chapters
    assert len(library.authors) > 0
    assert library.authors.issubset(authors_from_db)


def test_readers_contains_every_reader_from_db():
    from cozy.model.library import Library, split_strings_to_set
    from cozy.db.book import Book

    library = Library()
    books = Book.select(Book.reader).distinct().order_by(Book.reader)
    readers_from_db = [book.reader for book in books]
    readers_from_db = list(split_strings_to_set(set(readers_from_db)))

    # we cannot assert the same content as the library filters books without chapters
    assert len(library.readers) > 0
    assert library.readers.issubset(readers_from_db)


def test_deleted_chapter_removed_from_lists():
    from cozy.model.library import Library

    library = Library()

    chapter = next(iter(library.chapters))
    library._load_all_files()
    library._load_all_chapters()
    library._on_chapter_event("chapter-deleted", next(iter(library.chapters)))

    assert chapter not in library.chapters
    assert chapter.file not in library.files


def test_deleted_book_removed_from_list():
    from cozy.model.library import Library

    library = Library()

    book = next(iter(library.books))
    library._on_book_event("book-deleted", next(iter(library.books)))

    assert book not in library.books


def test_rebase_path():
    from cozy.model.library import Library

    library = Library()
    chapters = {chapter for chapter in library.chapters if chapter.file.startswith("20.000 Meilen unter dem Meer")}  # noqa: F841
    library.rebase_path("20.000 Meilen unter dem Meer", "new path")


def test_empty_last_book_returns_none():
    from cozy.model.library import Library

    library = Library()
    library._settings.last_played_book = None

    assert library.last_played_book is None


def test_library_last_book_returns_the_book_it_was_set_to():
    from cozy.model.library import Library

    library = Library()
    library._settings.last_played_book = library.books[0]

    assert library.last_played_book is library.books[0]

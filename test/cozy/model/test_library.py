import pytest
from peewee import SqliteDatabase

from cozy.application_settings import ApplicationSettings
from cozy.ext import inject
from cozy.extensions.set import split_strings_to_set
from cozy.model.settings import Settings
from test.cozy.mocks import ApplicationSettingsMock


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
    from cozy.model.library import Library
    from cozy.db.book import Book

    library = Library()
    books = Book.select(Book.author).distinct().order_by(Book.author)
    authors_from_db = [book.author for book in books]
    authors_from_db = list(split_strings_to_set(set(authors_from_db)))

    # we cannot assert the same content as the library filters books without chapters
    assert len(library.authors) > 0
    assert library.authors.issubset(authors_from_db)


def test_readers_contains_every_reader_from_db():
    from cozy.model.library import Library
    from cozy.db.book import Book

    library = Library()
    books = Book.select(Book.reader).distinct().order_by(Book.reader)
    readers_from_db = [book.reader for book in books]
    readers_from_db = list(split_strings_to_set(set(readers_from_db)))

    # we cannot assert the same content as the library filters books without chapters
    assert len(library.readers) > 0
    assert library.readers.issubset(readers_from_db)


def test_prepare_db_objects_skips_none():
    from cozy.model.library import Library
    library = Library()

    library._prepare_db_objects([None, None, None])


def xtest_update_track_db_object_updates_object():
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter
    from cozy.db.track import Track

    library = Library()

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[chapter])

    book = Book.select().get()

    library._update_track_db_object(media_file, book)

    track_in_db: Track = Track.select().where(Track.file == "test.mp3").get()

    assert track_in_db.name == "New Chapter"
    assert track_in_db.disk == 999
    assert track_in_db.number == 999
    assert track_in_db.length == 1234567
    assert track_in_db.modified == 1234567


def test_create_track_db_object_creates_object():
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    library = Library()

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="New File",
                           modified=1234567,
                           chapters=[chapter])

    book = Book.select().get()

    res_dict = library._get_track_list_for_db(media_file, book)[0]

    assert res_dict["name"] == "New Chapter"
    assert res_dict["disk"] == 999
    assert res_dict["number"] == 999
    assert res_dict["book"] == book
    assert res_dict["length"] == 1234567
    assert res_dict["modified"] == 1234567
    assert res_dict["position"] == 0


def test_update_book_db_object_updates_object():
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    library = Library()

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[chapter])

    library._update_book_db_object(media_file)

    book_in_db: Book = Book.select().where(Book.name == "Test Book").get()

    assert book_in_db.name == "Test Book"
    assert book_in_db.author == "New Author"
    assert book_in_db.reader == "New Reader"
    assert book_in_db.cover == b"cover"


def test_create_book_db_object_creates_object():
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    library = Library()

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="New Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[chapter])

    library._create_book_db_object(media_file)

    book_in_db: Book = Book.select().where(Book.name == "New Book").get()

    assert book_in_db.name == "New Book"
    assert book_in_db.author == "New Author"
    assert book_in_db.reader == "New Reader"
    assert book_in_db.cover == b"cover"
    assert book_in_db.position == 0
    assert book_in_db.rating == -1


def test_prepare_db_objects_updates_existing_track(mocker):
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    library = Library()
    spy = mocker.spy(library, "_update_track_db_object")

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[chapter])

    res_dict = library._prepare_db_objects([media_file])

    assert len(list(res_dict)) == 0
    spy.assert_called_once()


def test_prepare_db_objects_creates_new_track(mocker):
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    library = Library()
    spy = mocker.spy(library, "_get_track_list_for_db")

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="New test File",
                           modified=1234567,
                           chapters=[chapter])

    res_dict = library._prepare_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_prepare_db_objects_updates_existing_book(mocker):
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    library = Library()
    spy = mocker.spy(library, "_update_book_db_object")

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="New test File",
                           modified=1234567,
                           chapters=[chapter])

    res_dict = library._prepare_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_prepare_db_objects_creates_new_book(mocker):
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    library = Library()
    spy = mocker.spy(library, "_create_book_db_object")

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="New test File",
                           modified=1234567,
                           chapters=[chapter])

    res_dict = library._prepare_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_prepare_db_objects_raises_not_implemented_for_multi_chapter_file(mocker):
    from cozy.model.library import Library
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    library = Library()

    chapter = Chapter("New Chapter", 0)
    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="New test File",
                           modified=1234567,
                           chapters=[chapter, chapter])

    with pytest.raises(NotImplementedError):
        res_dict = library._prepare_db_objects([media_file])
        list(res_dict)


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
    chapters = {chapter for chapter in library.chapters if chapter.file.startswith("20.000 Meilen unter dem Meer")}
    library.rebase_path("20.000 Meilen unter dem Meer", "new path")


def test_empty_last_book_returns_none():
    from cozy.model.library import Library

    library = Library()
    library._settings.last_played_book = None

    assert library.last_played_book is None


def test_empty_last_book_returns_none():
    from cozy.model.library import Library

    library = Library()
    library._settings.last_played_book = library.books[0]

    assert library.last_played_book is library.books[0]

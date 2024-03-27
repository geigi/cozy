import pytest
from peewee import SqliteDatabase

from cozy.application_settings import ApplicationSettings
from cozy.ext import inject
from test.cozy.mocks import ApplicationSettingsMock


@pytest.fixture(autouse=True)
def setup_inject(peewee_database):
    inject.clear_and_configure(lambda binder: binder
                               .bind(SqliteDatabase, peewee_database)
                               .bind_to_constructor(ApplicationSettings, lambda: ApplicationSettingsMock()))
    yield
    inject.clear()


def test_db_created(peewee_database):
    from cozy.db.book import Book

    assert Book.table_exists()


def test_name_returns_correct_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.name == "Test Book"


def test_setting_name_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.name = "Altered"
    assert book.name == "Altered"
    assert BookDB.get_by_id(1).name == "Altered"


def test_author_returns_correct_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.author == "Test Author"


def test_setting_author_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.author = "Altered"
    assert book.author == "Altered"
    assert BookDB.get_by_id(1).author == "Altered"


def test_reader_returns_correct_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.reader == "Test Reader"


def test_setting_reader_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.reader = "Altered"
    assert book.reader == "Altered"
    assert BookDB.get_by_id(1).reader == "Altered"


def test_position_returns_default_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.position == 0


def test_setting_position_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.position = 42
    assert book.position == 42
    assert BookDB.get_by_id(1).position == 42


def test_rating_returns_default_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.rating == 0


def test_setting_rating_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.rating = 5
    assert book.rating == 5
    assert BookDB.get_by_id(1).rating == 5


def test_cover_returns_default_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.cover is None


def test_setting_cover_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.cover = b"42"
    assert book.cover == b"42"
    assert BookDB.get_by_id(1).cover == b"42"


def test_playback_speed_returns_default_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.playback_speed == 1.0


def test_setting_playback_speed_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.playback_speed = 1.2
    assert book.playback_speed == 1.2
    assert BookDB.get_by_id(1).playback_speed == 1.2


def test_last_played_returns_default_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.last_played == 0


def test_setting_last_played_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.last_played = 42
    assert book.last_played == 42
    assert BookDB.get_by_id(1).last_played == 42


def test_offline_returns_default_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.offline is False


def test_setting_offline_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.offline = True
    assert book.offline is True
    assert BookDB.get_by_id(1).offline is True


def test_downloaded_returns_default_value(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert book.downloaded is False


def test_setting_downloaded_updates_in_book_object_and_database(peewee_database):
    from cozy.db.book import Book as BookDB
    from cozy.model.book import Book

    book = Book(peewee_database, BookDB.get(1))
    book.downloaded = True
    assert book.downloaded is True
    assert BookDB.get_by_id(1).downloaded is True


def test_chapters_return_correct_count_of_chapters(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    assert len(book.chapters) == 1


def test_tracks_are_ordered_by_disk_number_name(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(9))

    chapters_manually_sorted = book.chapters.copy()
    chapters_manually_sorted.sort(key=lambda chapter: (chapter.disk, chapter.number, chapter.name))

    assert all(a == b for a, b in zip(book.chapters, chapters_manually_sorted))


def test_current_track_is_actually_current_track(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(9))

    assert book.current_chapter.id == BookDB.get_by_id(9).position


def test_try_to_init_empty_book_should_throw_exception(peewee_database):
    from cozy.model.book import Book
    from cozy.model.book import BookIsEmpty
    from cozy.db.book import Book as BookDB

    with pytest.raises(BookIsEmpty):
        Book(peewee_database, BookDB.get(10))


def test_try_to_init_non_existant_book_throws_exception(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB
    from peewee import DoesNotExist

    with pytest.raises(DoesNotExist):
        Book(peewee_database, BookDB.get(-42))


def test_delete_deletes_book_from_db(peewee_database, mocker):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    spy = mocker.spy(book, "emit_event")
    book._on_chapter_event("chapter-deleted", book.chapters[0])

    assert BookDB.select().where(BookDB.id == 1).count() < 1
    spy.assert_called_once_with("book-deleted", book)
    assert len(book._listeners) < 1


def test_deleted_book_removed_from_last_played_book_if_necessary(peewee_database):
    from cozy.model.book import Book
    from cozy.model.settings import Settings
    from cozy.db.book import Book as BookDB

    settings = Settings()
    inject.clear_and_configure(
        lambda binder: binder.bind(SqliteDatabase, peewee_database) and binder.bind(Settings, settings))
    book = Book(peewee_database, BookDB.get(1))

    settings.last_played_book = book
    book._on_chapter_event("chapter-deleted", book.chapters[0])

    assert settings.last_played_book is None


def test_skipping_removing_a_non_existing_chapter(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    book._on_chapter_event("chapter-deleted", None)


def test_progress_return_progress_for_started_book(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    chapter = book.chapters[0]
    chapter.position = 42 * 1000000000
    book.position = chapter.id

    assert book.progress == 42


def test_progress_should_be_zero_for_unstarted_book(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    book.position = 0

    assert book.progress == 0


def test_progress_should_be_100_for_finished_book(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB

    book = Book(peewee_database, BookDB.get(1))
    book.position = -1

    assert book.progress == book.duration


def test_removing_book_removes_all_traces_in_db(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB
    from cozy.db.track import Track
    from cozy.db.file import File
    from cozy.db.track_to_file import TrackToFile

    book = Book(peewee_database, BookDB.get(1))
    track_ids = [chapter.id for chapter in book.chapters]
    track_to_file_ids = [track_to_file.id for track_to_file in
                         TrackToFile.select().join(Track).where(TrackToFile.track.id << track_ids)]
    file_ids = [track_to_file.file.id for track_to_file in
                TrackToFile.select().join(Track).where(TrackToFile.track.id << track_ids)]

    assert len(track_ids) > 0
    assert len(track_to_file_ids) > 0
    assert len(file_ids) > 0

    book.remove()

    assert BookDB.select().where(BookDB.id == 1).count() == 0
    assert Track.select().where(Track.id << track_ids).count() == 0
    assert TrackToFile.select().where(TrackToFile.id << track_to_file_ids).count() == 0
    assert File.select().where(File.id << file_ids).count() == 0


def test_removing_book_with_missing_file_removes_all_traces_in_db(peewee_database):
    from cozy.model.book import Book
    from cozy.db.book import Book as BookDB
    from cozy.db.track import Track
    from cozy.db.file import File
    from cozy.db.track_to_file import TrackToFile

    book = Book(peewee_database, BookDB.get(1))
    track_ids = [chapter.id for chapter in book.chapters]
    track_to_file_ids = [track_to_file.id for track_to_file in
                         TrackToFile.select().join(Track).where(TrackToFile.track.id << track_ids)]
    file_ids = [track_to_file.file.id for track_to_file in
                TrackToFile.select().join(Track).where(TrackToFile.track.id << track_ids)]

    assert len(track_ids) > 0
    assert len(track_to_file_ids) > 0
    assert len(file_ids) > 0

    File.get_by_id(file_ids[0]).delete_instance()

    book.remove()

    assert BookDB.select().where(BookDB.id == 1).count() == 0
    assert Track.select().where(Track.id << track_ids).count() == 0
    assert TrackToFile.select().where(TrackToFile.id << track_to_file_ids).count() == 0
    assert File.select().where(File.id << file_ids).count() == 0

import pytest
from peewee import SqliteDatabase

from cozy.ext import inject


@pytest.fixture(autouse=True)
def setup_inject(peewee_database):
    inject.clear()
    inject.configure(lambda binder: (binder.bind(SqliteDatabase, peewee_database)))
    yield
    inject.clear()


def test_prepare_files_db_objects_skips_existing_files():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile

    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[None])

    database_importer = DatabaseImporter()
    file_objects = database_importer._prepare_files_db_objects([media_file])
    assert len(file_objects) == 0


def test_update_files_db_objects_updates_modified_field():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.file import File

    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="test.mp3",
                           modified=12345678,
                           chapters=[None])

    database_importer = DatabaseImporter()
    file = File.select().where(File.path == "test.mp3").get()
    file_objects = database_importer._update_files_in_db(file, media_file)

    assert File.select().where(File.path == "test.mp3").get().modified == 12345678


def test_prepare_files_db_objects_returns_object_for_new_file():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile

    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="i_m_a_new_file.mp3",
                           modified=1234567,
                           chapters=[None])

    database_importer = DatabaseImporter()
    file_objects = database_importer._prepare_files_db_objects([media_file])
    assert len(file_objects) == 1
    assert file_objects[0]["path"] == "i_m_a_new_file.mp3"


def test_prepare_db_objects_skips_none():
    from cozy.model.database_importer import DatabaseImporter
    database_importer = DatabaseImporter()

    database_importer._prepare_track_db_objects([None, None, None])


def test_update_track_db_object_updates_object():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter
    from cozy.db.track import Track
    from cozy.db.file import File
    from cozy.db.track_to_file import TrackToFile

    database_importer = DatabaseImporter()

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

    database_importer._update_track_db_object(media_file, book)

    track_to_file: TrackToFile = TrackToFile.select().join(File).where(TrackToFile.file.path == "test.mp3").get()
    track: Track = track_to_file.track

    assert track.name == "New Chapter"
    assert track.disk == 999
    assert track.number == 999
    assert track.length == 1234567


def test_create_track_db_object_creates_object():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

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

    res_dict = database_importer._get_track_list_for_db(media_file, book)[0]

    assert res_dict["name"] == "New Chapter"
    assert res_dict["disk"] == 999
    assert res_dict["number"] == 999
    assert res_dict["book"] == book
    assert res_dict["length"] == 1234567
    assert res_dict["modified"] == 1234567
    assert res_dict["position"] == 0


def test_update_book_db_object_updates_object():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

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

    database_importer._update_book_db_object(media_file)

    book_in_db: Book = Book.select().where(Book.name == "Test Book").get()

    assert book_in_db.name == "Test Book"
    assert book_in_db.author == "New Author"
    assert book_in_db.reader == "New Reader"
    assert book_in_db.cover == b"cover"


def test_create_book_db_object_creates_object():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

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

    database_importer._create_book_db_object(media_file)

    book_in_db: Book = Book.select().where(Book.name == "New Book").get()

    assert book_in_db.name == "New Book"
    assert book_in_db.author == "New Author"
    assert book_in_db.reader == "New Reader"
    assert book_in_db.cover == b"cover"
    assert book_in_db.position == 0
    assert book_in_db.rating == -1


def test_prepare_db_objects_updates_existing_track(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_update_track_db_object")

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

    res_dict = database_importer._prepare_track_db_objects([media_file])

    assert len(list(res_dict)) == 0
    spy.assert_called_once()


def test_prepare_db_objects_creates_new_track(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_get_track_list_for_db")

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

    res_dict = database_importer._prepare_track_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_prepare_db_objects_updates_existing_book(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_update_book_db_object")

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

    res_dict = database_importer._prepare_track_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_prepare_db_objects_creates_new_book(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_create_book_db_object")

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

    res_dict = database_importer._prepare_track_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_delete_all_tracks_from_db_does_as_it_says():
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter
    from cozy.db.file import File
    from cozy.db.track import Track
    from cozy.db.track_to_file import TrackToFile
    from cozy.model.database_importer import DatabaseImporter

    database_importer = DatabaseImporter()

    chapter = Chapter("Ohne Aussicht auf Freiheit", 0)
    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="20.000 Meilen unter dem Meer/2-10 Ohne Aussicht auf Freiheit.m4a",
                           modified=1234567,
                           chapters=[chapter])

    assert Track.select().where(Track.name == "Ohne Aussicht auf Freiheit").count() == 1
    assert TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path).count() == 1

    database_importer._delete_tracks_from_db(media_file)
    assert Track.select().where(Track.name == "Ohne Aussicht auf Freiheit").count() == 0
    assert TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path).count() == 0
    assert File.select().where(File.path == media_file.path).count() == 1


def test_delete_all_tracks_from_db_does_nothing_if_no_tracks_are_present():
    from cozy.media.media_file import MediaFile
    from cozy.model.database_importer import DatabaseImporter

    database_importer = DatabaseImporter()

    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="file_not_present",
                           modified=1234567,
                           chapters=[])

    database_importer._delete_tracks_from_db(media_file)


def test_is_chapter_count_in_db_different_returns_true_for_non_existent_file():
    from cozy.media.media_file import MediaFile
    from cozy.model.database_importer import DatabaseImporter

    database_importer = DatabaseImporter()

    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="file_not_present",
                           modified=1234567,
                           chapters=["Chapter 1"])

    assert database_importer._is_chapter_count_in_db_different(media_file)


def test_is_chapter_count_in_db_different_returns_false_for_equal_chapter_count():
    from cozy.media.media_file import MediaFile
    from cozy.model.database_importer import DatabaseImporter

    database_importer = DatabaseImporter()

    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           track_number=999,
                           length=1234567,
                           cover=b"cover",
                           path="20.000 Meilen unter dem Meer/2-10 Ohne Aussicht auf Freiheit.m4a",
                           modified=1234567,
                           chapters=[None])

    assert not database_importer._is_chapter_count_in_db_different(media_file)

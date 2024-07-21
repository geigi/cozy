import inject
import pytest
from peewee import SqliteDatabase


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
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[None])

    database_importer = DatabaseImporter()
    file_objects = database_importer._prepare_files_db_objects([media_file])
    assert len(file_objects) == 0


def test_prepare_files_db_objects_skips_duplicate_file():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile

    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="i_m_a_new_file.mp3",
                           modified=1234567,
                           chapters=[None])

    database_importer = DatabaseImporter()
    file_objects = database_importer._prepare_files_db_objects([media_file, media_file])
    assert len(file_objects) == 1
    assert file_objects[0]["path"] == "i_m_a_new_file.mp3"


def test_update_files_db_objects_updates_modified_field():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.file import File

    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="test.mp3",
                           modified=12345678,
                           chapters=[None])

    database_importer = DatabaseImporter()
    file = File.select().where(File.path == "test.mp3").get()
    database_importer._update_files_in_db(file, media_file)

    assert File.select().where(File.path == "test.mp3").get().modified == 12345678


def test_prepare_files_db_objects_returns_object_for_new_file():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile

    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
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


def test_create_track_db_object_creates_object():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="New Book Name",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
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
    assert res_dict["position"] == 0


def test_update_book_db_object_updates_object():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
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


def test_update_book_db_object_updates_object_regardless_of_book_spelling():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="TEST BOOK",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[chapter])

    database_importer._update_book_db_object(media_file)

    book_in_db: Book = Book.select().where(Book.name == "TEST BOOK").get()

    assert book_in_db.name == "TEST BOOK"
    assert book_in_db.author == "New Author"
    assert book_in_db.reader == "New Reader"
    assert book_in_db.cover == b"cover"


def test_create_book_db_object_creates_object():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.db.book import Book
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="New Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
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


def test_prepare_db_objects_recreates_existing_track(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter
    from cozy.db.track_to_file import TrackToFile
    from cozy.db.file import File

    database_importer = DatabaseImporter()

    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="test.mp3",
                           modified=1234567,
                           chapters=[chapter])

    res = database_importer._prepare_track_db_objects([media_file])
    res_list = list(res)
    request = res_list[0]

    assert TrackToFile.select().join(File).where(File.path == "test.mp3").count() == 0

    assert len(res_list) == 1
    assert request.file.path == "test.mp3"
    assert request.start_at == 0
    assert request.track_data["name"] == "New Chapter"
    assert request.track_data["number"] == 999
    assert request.track_data["disk"] == 999
    assert request.track_data["book"].id == 1
    assert request.track_data["length"] == 1234567
    assert request.track_data["position"] == 0


def test_prepare_db_objects_skips_if_file_object_not_present(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter

    database_importer = DatabaseImporter()

    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="New test File",
                           modified=1234567,
                           chapters=[chapter])

    res_dict = database_importer._prepare_track_db_objects([media_file])

    assert len(list(res_dict)) == 0


def test_prepare_db_objects_creates_new_track(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter
    from cozy.db.file import File

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_get_track_list_for_db")

    File.create(path="New File", modified=1234567)
    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="New File",
                           modified=1234567,
                           chapters=[chapter])

    res_dict = database_importer._prepare_track_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_prepare_db_objects_updates_existing_book(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter
    from cozy.db.file import File

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_update_book_db_object")

    File.create(path="New test File", modified=1234567)
    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="Test Book",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="New test File",
                           modified=1234567,
                           chapters=[chapter])

    res_dict = database_importer._prepare_track_db_objects([media_file])

    assert len(list(res_dict)) == 1
    spy.assert_called_once()


def test_prepare_db_objects_updates_existing_book_regardless_of_spelling(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter
    from cozy.db.file import File

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_update_book_db_object")

    File.create(path="New test File", modified=1234567)
    File.create(path="Another test File", modified=1234568)
    chapter = Chapter("New Chapter", 0, 1234567, 999)
    another_chapter = Chapter("Another Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="TeSt bOOk",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="New test File",
                           modified=1234567,
                           chapters=[chapter])
    another_media_file = MediaFile(book_name="TEST BOOK",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
                           cover=b"cover",
                           path="Another test File",
                           modified=1234568,
                           chapters=[another_chapter])

    res_dict = database_importer._prepare_track_db_objects([media_file, another_media_file])

    assert len(list(res_dict)) == 2
    spy.assert_called_once()


def test_prepare_db_objects_creates_new_book(mocker):
    from cozy.model.database_importer import DatabaseImporter
    from cozy.media.media_file import MediaFile
    from cozy.media.chapter import Chapter
    from cozy.db.file import File

    database_importer = DatabaseImporter()
    spy = mocker.spy(database_importer, "_create_book_db_object")

    File.create(path="New test File", modified=1234567)
    chapter = Chapter("New Chapter", 0, 1234567, 999)
    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
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

    chapter = Chapter("Ohne Aussicht auf Freiheit", 0, 1234567, 999)
    media_file = MediaFile(book_name="Test Book New",
                           author="New Author2",
                           reader="New Reader",
                           disk=999,
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
                           cover=b"cover",
                           path="20.000 Meilen unter dem Meer/2-10 Ohne Aussicht auf Freiheit.m4a",
                           modified=1234567,
                           chapters=[None])

    assert not database_importer._is_chapter_count_in_db_different(media_file)


def test_insert_track_inserts_all_rows_expected():
    from cozy.model.database_importer import DatabaseImporter, TrackInsertRequest
    from cozy.db.book import Book
    from cozy.db.file import File
    from cozy.db.track_to_file import TrackToFile

    database_importer = DatabaseImporter()

    file = File.create(path="New File", modified=1234567)
    track_data = {
        "name": "Test",
        "number": 2,
        "disk": 2,
        "book": Book.select().where(Book.name == "Test Book").get(),
        "length": 123,
        "position": 0
    }

    track = TrackInsertRequest(track_data, file, 1234)

    database_importer._insert_tracks([track])
    track_to_file_query = TrackToFile.select().join(File).where(TrackToFile.file == file.id)
    assert track_to_file_query.count() == 1

    track_to_file: TrackToFile = track_to_file_query.get()

    assert track_to_file.track.name == track_data["name"]
    assert track_to_file.track.number == track_data["number"]
    assert track_to_file.track.disk == track_data["disk"]
    assert track_to_file.track.book.id == Book.select().where(Book.name == "Test Book").get().id
    assert track_to_file.track.length == track_data["length"]
    assert track_to_file.track.position == track_data["position"]


def test_update_book_position_skips_empty_book():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.db.book import Book

    database_importer = DatabaseImporter()

    book = Book.get_by_id(10)
    database_importer._update_book_position(book, 0)


def test_update_book_position_sets_position_for_multi_chapter_file_correctly():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.db.book import Book
    from cozy.db.track import Track

    database_importer = DatabaseImporter()

    book = Book.get_by_id(11)
    database_importer._update_book_position(book, 4251000000000)

    book = Book.get_by_id(11)
    assert book.position == 232
    assert Track.get_by_id(232).position == 4251000000000


def test_update_book_position_sets_position_for_single_chapter_file_correctly():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.db.book import Book
    from cozy.db.track import Track

    database_importer = DatabaseImporter()

    book = Book.get_by_id(2)
    database_importer._update_book_position(book, 4251000000000)

    book = Book.get_by_id(2)
    desired_chapter_position = 4251000000000 - ((Track.get_by_id(198).length + Track.get_by_id(197).length) * 1e9)
    assert book.position == 194
    assert Track.get_by_id(194).position == desired_chapter_position


def test_update_book_position_resets_position_if_it_is_longer_than_the_duration():
    from cozy.model.database_importer import DatabaseImporter
    from cozy.db.book import Book

    database_importer = DatabaseImporter()

    book = Book.get_by_id(11)
    book.position = 1
    book.save(only=book.dirty_fields)
    database_importer._update_book_position(book, 42510000000000)

    book = Book.get_by_id(11)
    assert book.position == 0

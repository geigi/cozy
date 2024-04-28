import json
import os

import pytest

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')


@pytest.fixture(scope='session', autouse=True)
def install_l10n():
    import gettext as g
    trans = g.translation('spam', 'locale', fallback=True)
    trans.install('gettext')


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@pytest.fixture(scope="function")
def peewee_database():
    from cozy.db.track import Track
    from cozy.db.book import Book
    from cozy.db.settings import Settings
    from cozy.db.storage_blacklist import StorageBlackList
    from cozy.db.storage import Storage
    from cozy.db.file import File
    from cozy.db.track_to_file import TrackToFile

    db_path, models, test_db = prepare_db()

    path_of_test_folder = os.path.dirname(os.path.realpath(__file__)) + '/'

    with open(path_of_test_folder + 'books.json') as json_file:
        book_data = json.load(json_file)

    with open(path_of_test_folder + 'tracks.json') as json_file:
        track_data = json.load(json_file)

    with open(path_of_test_folder + 'files.json') as json_file:
        file_data = json.load(json_file)

    with open(path_of_test_folder + 'track_to_file.json') as json_file:
        track_to_file_data = json.load(json_file)

    Book.insert_many(book_data).execute()
    for chunk in chunks(track_data, 25):
        Track.insert_many(chunk).execute()

    for chunk in chunks(file_data, 25):
        File.insert_many(chunk).execute()

    for chunk in chunks(track_to_file_data, 25):
        TrackToFile.insert_many(chunk).execute()

    with open(path_of_test_folder + 'storages.json') as json_file:
        storage_data = json.load(json_file)

    Storage.insert_many(storage_data).execute()

    Settings.create(path="", last_played_book=Book.get())
    StorageBlackList.create(path="/path/to/replace/test1.mp3")
    StorageBlackList.create(path="/path/to/not/replace/test2.mp3")

    print("Provide database...")
    yield test_db

    teardown_db(db_path, models, test_db)


@pytest.fixture(scope="function")
def peewee_database_storage():
    from cozy.db.storage import Storage
    from cozy.db.settings import Settings
    from cozy.db.storage_blacklist import StorageBlackList

    db_path, models, test_db = prepare_db()
    path_of_test_folder = os.path.dirname(os.path.realpath(__file__)) + '/'

    with open(path_of_test_folder + 'storages.json') as json_file:
        storage_data = json.load(json_file)

    Storage.insert_many(storage_data).execute()
    Settings.create(path="", last_played_book=None)
    StorageBlackList.create(path="/path/to/replace/test1.mp3")
    StorageBlackList.create(path="/path/to/not/replace/test2.mp3")

    print("Provide database...")
    yield test_db

    teardown_db(db_path, models, test_db)


def teardown_db(db_path, models, test_db):
    print("Teardown database...")
    test_db.drop_tables(models)
    test_db.close()


def prepare_db():
    from playhouse.pool import PooledSqliteDatabase
    from cozy.db.artwork_cache import ArtworkCache
    from cozy.db.book import Book
    from cozy.db.offline_cache import OfflineCache
    from cozy.db.settings import Settings
    from cozy.db.storage import Storage
    from cozy.db.storage_blacklist import StorageBlackList
    from cozy.db.track import Track
    from cozy.db.file import File
    from cozy.db.track_to_file import TrackToFile
    from cozy.db.collation import collate_natural

    models = [Track, Book, File, TrackToFile, Settings, ArtworkCache, Storage, StorageBlackList, OfflineCache]

    print("Setup database...")

    db_path = ':memory:'
    test_db = PooledSqliteDatabase(db_path, pragmas=[('journal_mode', 'wal')])
    test_db.bind(models, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(models)
    test_db.register_collation(collate_natural)

    return db_path, models, test_db

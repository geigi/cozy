import json
import os

import pytest


@pytest.fixture(scope='session', autouse=True)
def install_l10n():
    import gettext as g
    trans = g.translation('spam', 'locale', fallback=True)
    trans.install('gettext')


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@pytest.fixture(scope="module")
def peewee_database():
    from cozy.db.track import Track
    from cozy.db.book import Book
    from cozy.db.settings import Settings

    db_path, models, test_db = prepare_db()

    path_of_test_folder = os.path.dirname(os.path.realpath(__file__)) + '/'

    with open(path_of_test_folder + 'books.json') as json_file:
        book_data = json.load(json_file)

    with open(path_of_test_folder + 'tracks.json') as json_file:
        track_data = json.load(json_file)

    Book.insert_many(book_data).execute()
    for chunk in chunks(track_data, 25):
        Track.insert_many(chunk).execute()

    Settings.create(path="", last_played_book=None)

    print("Provide database...")
    yield test_db

    teardown_db(db_path, models, test_db)


@pytest.fixture(scope="module")
def peewee_database_storage():
    from cozy.db.storage import Storage
    from cozy.db.settings import Settings

    db_path, models, test_db = prepare_db()
    path_of_test_folder = os.path.dirname(os.path.realpath(__file__)) + '/'

    with open(path_of_test_folder + 'storages.json') as json_file:
        storage_data = json.load(json_file)

    Storage.insert_many(storage_data).execute()
    Settings.create(path="", last_played_book=None)

    print("Provide database...")
    yield test_db

    teardown_db(db_path, models, test_db)


def teardown_db(db_path, models, test_db):
    print("Teardown database...")
    test_db.drop_tables(models)
    test_db.close()
    os.remove(db_path)


def prepare_db():
    from playhouse.apsw_ext import APSWDatabase
    from cozy.db.artwork_cache import ArtworkCache
    from cozy.db.book import Book
    from cozy.db.offline_cache import OfflineCache
    from cozy.db.settings import Settings
    from cozy.db.storage import Storage
    from cozy.db.storage_blacklist import StorageBlackList
    from cozy.db.track import Track

    models = [Track, Book, Settings, ArtworkCache, Storage, StorageBlackList, OfflineCache]

    print("Setup database...")

    db_path = '/tmp/cozy_test.db'
    test_db = APSWDatabase(db_path, pragmas=[('journal_mode', 'wal')])
    test_db.bind(models, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(models)

    return db_path, models, test_db

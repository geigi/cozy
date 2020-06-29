import json
import os

import pytest


@pytest.fixture(scope="module")
def peewee_database():
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
    test_db = APSWDatabase(db_path, max_connections=32)
    test_db.bind(models, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(models)

    path_of_test_folder = os.path.dirname(os.path.realpath(__file__)) + '/'

    with open(path_of_test_folder + 'books.json') as json_file:
        book_data = json.load(json_file)

    with open(path_of_test_folder + 'tracks.json') as json_file:
        track_data = json.load(json_file)

    Book.insert_many(book_data).execute()
    Track.insert_many(track_data).execute()

    print("Provide database...")
    yield test_db

    print("Teardown database...")
    test_db.drop_tables(models)
    test_db.close()
    os.remove(db_path)

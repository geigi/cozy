import pytest


@pytest.fixture
def peewee_database():
    from peewee import SqliteDatabase

    from cozy.model.artwork_cache import ArtworkCache
    from cozy.model.book import Book
    from cozy.model.offline_cache import OfflineCache
    from cozy.model.settings import Settings
    from cozy.model.storage import Storage
    from cozy.model.storage_blacklist import StorageBlackList
    from cozy.model.track import Track

    MODELS = [Track, Book, Settings, ArtworkCache, Storage, StorageBlackList, OfflineCache]

    print("Setup database...")
    test_db = SqliteDatabase(':memory:')
    test_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(MODELS)

    print("Provide database...")
    yield test_db

    print("Teardown database...")
    test_db.drop_tables(MODELS)
    test_db.close()


def test_db_created(peewee_database):
    from cozy.model.book import Book

    with peewee_database:
        assert Book.table_exists()

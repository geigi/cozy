import pytest


@pytest.fixture
def peewee_database():
    from peewee import SqliteDatabase

    from cozy.db.artwork_cache import ArtworkCache
    from cozy.db.book import Book
    from cozy.db.offline_cache import OfflineCache
    from cozy.db.settings import Settings
    from cozy.db.storage import Storage
    from cozy.db.storage_blacklist import StorageBlackList
    from cozy.db.track import Track

    models = [Track, Book, Settings, ArtworkCache, Storage, StorageBlackList, OfflineCache]

    print("Setup database...")
    test_db = SqliteDatabase('/tmp/cozy_test.db')
    test_db.bind(models, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(models)

    book = Book.create(name="Test Book", author="Test Author", reader="Test Reader", position=0, rating=0)
    Book.create(name="Test Book 2", author="Test Author 2", reader="Test Reader 2", position=0, rating=0)
    track = Track.create(name="Test Track", number=1, disk=1, position=0, book=book, file="test.mp3", length=42.1,
                         modified=123456)

    print("Provide database...")
    yield test_db

    print("Teardown database...")
    test_db.drop_tables(models)
    test_db.close()

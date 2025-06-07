import inject
import pytest
from peewee import SqliteDatabase


@pytest.fixture(autouse=True)
def setup_inject(peewee_database):
    inject.clear_and_configure(lambda binder: binder.bind(SqliteDatabase, peewee_database))
    yield
    inject.clear()


def test_storage_locations_contains_every_storage_location_from_db(peewee_database):
    from cozy.db.storage import Storage
    from cozy.model.settings import Settings

    settings = Settings()
    storage_locations = Storage.select()

    assert len(settings.storage_locations) == len(storage_locations)
    assert [storage.path for storage in settings.storage_locations] == [storage.path for storage in storage_locations]
    assert [storage.location_type for storage in settings.storage_locations] == [storage.location_type for storage in
                                                                                 storage_locations]
    assert [storage.default for storage in settings.storage_locations] == [storage.default for storage in
                                                                           storage_locations]
    assert [storage.external for storage in settings.storage_locations] == [storage.external for storage in
                                                                            storage_locations]


def test_external_storage_locations_contain_only_external_storages(peewee_database):
    from cozy.db.storage import Storage
    from cozy.model.settings import Settings

    settings = Settings()
    storage_locations = Storage.select().where(Storage.external)

    assert len(settings.external_storage_locations) == len(storage_locations)
    assert all(storage.external for storage in settings.external_storage_locations)


def test_last_played_book_returns_correct_value(peewee_database):
    from cozy.db.book import Book
    from cozy.model.settings import Settings

    settings = Settings()

    assert settings.last_played_book == Book.get()


def test_setting_last_played_book_to_none_updates_in_settings_object_and_database(peewee_database):
    from cozy.db.settings import Settings as SettingsModel
    from cozy.model.settings import Settings

    settings = Settings()
    settings.last_played_book = None

    assert settings.last_played_book is None
    assert SettingsModel.get().last_played_book is None


def test_fetching_non_existent_last_played_book_returns_none(peewee_database):
    from cozy.db.settings import Settings as SettingsModel
    from cozy.model.settings import Settings

    db_object = SettingsModel.get()
    db_object.last_played_book = 437878782
    db_object.save(only=db_object.dirty_fields)

    settings = Settings()

    assert settings.last_played_book is None


def test_fetching_non_existent_last_played_book_sets_it_to_none(peewee_database):
    from cozy.db.settings import Settings as SettingsModel
    from cozy.model.settings import Settings

    db_object = SettingsModel.get()
    db_object.last_played_book = 437878782
    db_object.save(only=db_object.dirty_fields)

    settings = Settings()

    assert hasattr(settings, "last_played_book")
    assert SettingsModel.get().last_played_book is None


def test_ensure_default_storage_is_present_adds_default_if_not_present(peewee_database):
    from cozy.db.storage import Storage
    from cozy.model.settings import Settings

    Storage.update(default=False).where(Storage.id == 2).execute()

    settings = Settings()
    settings._load_all_storage_locations()
    settings._ensure_default_storage_is_present()
    assert Storage.get(1).default
    assert not Storage.get(2).default


def test_ensure_default_storage_is_present_does_nothing_if_default_is_present(peewee_database):
    from cozy.db.storage import Storage
    from cozy.model.settings import Settings

    settings = Settings()
    settings._load_all_storage_locations()
    settings._ensure_default_storage_is_present()
    assert not Storage.get(1).default
    assert Storage.get(2).default

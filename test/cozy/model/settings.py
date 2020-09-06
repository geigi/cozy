import inject
from peewee import SqliteDatabase


def test_storage_locations_contains_every_storage_location_from_db(peewee_database_storage):
    from cozy.model.settings import Settings
    from cozy.db.storage import Storage

    inject.clear_and_configure(lambda binder: binder
                               .bind(SqliteDatabase, peewee_database_storage))

    settings = Settings()
    storage_locations = Storage.select()

    assert len(settings.storage_locations) == len(storage_locations)
    assert [storage.path for storage in settings.storage_locations] == [storage.path for storage in storage_locations]
    assert [storage.location_type for storage in settings.storage_locations] == [storage.location_type for storage in storage_locations]
    assert [storage.default for storage in settings.storage_locations] == [storage.default for storage in storage_locations]
    assert [storage.external for storage in settings.storage_locations] == [storage.external for storage in storage_locations]

    inject.clear()

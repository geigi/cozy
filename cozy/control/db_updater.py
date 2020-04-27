import os

from peewee import IntegerField, BooleanField, FloatField
from playhouse.migrate import SqliteMigrator, migrate

from cozy.control.application_directories import get_cache_dir
from cozy.db.model_base import get_data_dir, get_sqlite_database
from cozy.db.offline_cache import OfflineCache
from cozy.db.settings import Settings
from cozy.db.storage import Storage
from cozy.db.storage_blacklist import StorageBlackList


def __update_db_1(db):
    migrator = SqliteMigrator(db)

    version = IntegerField(default=1)
    crc32 = BooleanField(default=False)

    migrate(
        migrator.add_column('settings', 'version', version),
        migrator.add_column('track', 'crc32', crc32),
    )


def __update_db_2(db):
    migrator = SqliteMigrator(db)

    playback_speed = FloatField(default=1.0)

    migrate(
        migrator.add_column('book', 'playback_speed', playback_speed),
    )

    Settings.update(version=2).execute()


def __update_db_3(db):
    current_path = Settings.get().path

    db.create_tables([Storage])
    Storage.create(path=current_path, default=True)
    Settings.update(path="NOT_USED").execute()
    Settings.update(version=3).execute()


def __update_db_4(db):
    migrator = SqliteMigrator(db)

    last_played = IntegerField(default=0)

    migrate(
        migrator.add_column('book', 'last_played', last_played),
    )

    Settings.update(version=4).execute()


def __update_db_5(db):
    db.create_tables([StorageBlackList])

    Settings.update(version=5).execute()


def __update_db_6(db):
    migrator = SqliteMigrator(db)

    db.create_tables([OfflineCache])

    external = BooleanField(default=False)
    offline = BooleanField(default=False)
    downloaded = BooleanField(default=False)

    migrate(
        migrator.add_column('storage', 'external', external),
        migrator.add_column('book', 'offline', offline),
        migrator.add_column('book', 'downloaded', downloaded)
    )

    Settings.update(version=6).execute()

    import shutil
    shutil.rmtree(get_cache_dir())


def __update_db_7(db):
    import cozy.control.artwork_cache as artwork_cache
    artwork_cache.delete_artwork_cache()
    Settings.update(version=7).execute()


def __update_db_8(db):
    db.execute_sql('UPDATE track SET modified=0 WHERE crc32=1')

    migrator: SqliteMigrator = SqliteMigrator(db)

    migrate(
        migrator.drop_column("track", "crc32")
    )

    Settings.update(version=8).execute()


def update_db():
    db = get_sqlite_database()
    # First test for version 1
    try:
        next(c for c in db.get_columns("settings") if c.name == "version")
    except Exception as e:
        if len(db.get_tables()) == 0:
            data_dir = get_data_dir()
            if os.path.exists(os.path.join(data_dir, "cozy.db")):
                os.remove(os.path.join(data_dir, "cozy.db"))
                os.remove(os.path.join(data_dir, "cozy.db-shm"))
                os.remove(os.path.join(data_dir, "cozy.db-wal"))
        __update_db_1(db)

    version = Settings.get().version
    # then for version 2 and so on
    if version < 2:
        __update_db_2(db)

    if version < 3:
        __update_db_3(db)

    if version < 4:
        __update_db_4(db)

    if version < 5:
        __update_db_5(db)

    if version < 6:
        __update_db_6(db)

    if version < 7:
        __update_db_7(db)

    if version < 8:
        __update_db_8(db)

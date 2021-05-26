import logging
import os
import shutil
from datetime import datetime
from typing import List

from peewee import IntegerField, BooleanField, FloatField, ForeignKeyField, fn
from playhouse.migrate import SqliteMigrator, migrate
from playhouse.reflection import generate_models

from cozy.control.application_directories import get_cache_dir
from cozy.db.file import File
from cozy.db.model_base import get_data_dir, get_sqlite_database
from cozy.db.offline_cache import OfflineCache
from cozy.db.settings import Settings
from cozy.db.storage import Storage
from cozy.db.storage_blacklist import StorageBlackList
from cozy.db.track import Track
from cozy.db.track_to_file import TrackToFile
from cozy.report import reporter

log = logging.getLogger("db_updater")


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
    from cozy.control.artwork_cache import ArtworkCache
    artwork_cache = ArtworkCache()
    artwork_cache.delete_artwork_cache()
    Settings.update(version=7).execute()


def __update_db_8(db):
    db.execute_sql('UPDATE track SET modified=0 WHERE crc32=1')

    migrator: SqliteMigrator = SqliteMigrator(db)

    migrate(
        migrator.drop_column("track", "crc32")
    )

    Settings.update(version=8).execute()


def _update_db_9(db):
    log.info("Migrating to DB Version 9...")

    models = generate_models(db)

    migrator: SqliteMigrator = SqliteMigrator(db)

    db.create_tables([File, TrackToFile])
    db.stop()
    db.start()

    files: List[File] = []
    track_to_files: List[TrackToFile] = []
    file_id = 1

    if "file" in models["track"]._meta.sorted_field_names:
        log.info("Generating File and TrackToFile objects...")
        for track in models["track"].select():
            path = track.file

            if File.select().where(File.path == path).count() > 0:
                log.info("Path already existing in db: {}".format(path))
                file = File.select().where(File.path == path).get()
            else:
                file = File(path=path, modified=track.modified, id=file_id)
                file_id += 1

            if TrackToFile.select().join(Track).where(TrackToFile.track.id == track.id).count() > 0:
                log.info("TrackToFile already existing in db: {}".format(path))
                continue

            track_to_file = TrackToFile(track=track, file=file, start_at=0)

            files.append(file)
            track_to_files.append(track_to_file)

        log.info("Inserting File and TrackToFile objects...")
        File.bulk_create(files, batch_size=300)
        TrackToFile.bulk_create(track_to_files, batch_size=300)

    field = ForeignKeyField(File, null=True, field=File.id)

    if "cached_file" not in models["offlinecache"]._meta.sorted_field_names:
        log.info("Rename in OfflineCache: file to cached_file...")
        migrate(
            migrator.rename_column("offlinecache", "file", "cached_file"),
        )

    if "original_file" not in models["offlinecache"]._meta.sorted_field_names:
        log.info("Add in OfflineCache: original_file_id...")
        migrate(
            migrator.add_column("offlinecache", "original_file_id", field)
        )

    db.stop()
    db.start()
    models = generate_models(db)

    if "file" in models["track"]._meta.sorted_field_names:
        log.info("Migrating OfflineCache...")
        for cache in models["offlinecache"].select():
            file_query = File.select().where(File.path == cache.track.file)
            if file_query.count() < 0:
                cache.delete_instance()

            file = file_query.get()
            cache.original_file = file
            cache.save(only=cache.dirty_fields)

    if "file" in models["track"]._meta.sorted_field_names:
        log.info("Drop in Track: file...")
        migrate(
            migrator.drop_column("track", "file")
        )

    if "modified" in models["track"]._meta.sorted_field_names:
        log.info("Drop in Track: modified...")
        migrate(
            migrator.drop_column("track", "modified")
        )

    if "track_id" in models["offlinecache"]._meta.sorted_field_names:
        log.info("Drop in OfflineCache: track_id...")
        migrate(
            migrator.drop_column("offlinecache", "track_id")
        )

    migrate(
        migrator.add_not_null("offlinecache", "original_file_id")
    )

    db.stop()
    db.start()

    log.info("Reset modified on all m4b files")
    File.update(modified=0).where(fn.Lower(File.path).endswith("m4b")).execute()

    Settings.update(version=9).execute()


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

    if version < 9:
        _backup_db(db)
        try:
            _update_db_9(db)
        except Exception as e:
            log.error(e)
            reporter.exception("db_updator", e)
            from cozy.ui.db_migration_failed_view import DBMigrationFailedView
            dialog = DBMigrationFailedView()
            dialog.show()
            exit(1)


def _backup_db(db):
    log.info("Backing up DB...")
    db.stop()
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H-%M-%S")
    backup_dir = os.path.join(get_data_dir(), dt_string)
    os.makedirs(backup_dir, exist_ok=True)

    db_path = os.path.join(get_data_dir(), "cozy.db")
    shm_path = os.path.join(get_data_dir(), "cozy.db-shm")
    wal_path = os.path.join(get_data_dir(), "cozy.db-wal")

    if os.path.exists(db_path):
        shutil.copyfile(db_path, os.path.join(backup_dir, "cozy.db"))

    if os.path.exists(shm_path):
        shutil.copyfile(shm_path, os.path.join(backup_dir, "cozy.db-shm"))

    if os.path.exists(wal_path):
        shutil.copyfile(wal_path, os.path.join(backup_dir, "cozy.db-wal"))

    db.start()

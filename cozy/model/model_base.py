import logging
import os

from gi.repository import GLib
from peewee import Model
from playhouse.sqliteq import SqliteQueueDatabase

log = logging.getLogger("db")

_db = None


def get_sqlite_database():
    global _db
    return _db


def get_data_dir():
    return os.path.join(GLib.get_user_data_dir(), "cozy")


def database_file_exists():
    return os.path.exists(os.path.join(get_data_dir(), "cozy.db"))


def __open_database():
    global _db
    if not os.path.exists(get_data_dir()):
        os.makedirs(get_data_dir())
    _db = SqliteQueueDatabase(os.path.join(get_data_dir(), "cozy.db"), pragmas=[('journal_mode', 'wal')])


__open_database()


class ModelBase(Model):
    class Meta:
        database = _db

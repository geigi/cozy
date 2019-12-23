import logging
import os

from gi.repository import GLib
from peewee import Model
from playhouse.sqliteq import SqliteQueueDatabase

log = logging.getLogger("db")

data_dir = os.path.join(GLib.get_user_data_dir(), "cozy")

update = None
if os.path.exists(os.path.join(data_dir, "cozy.db")):
    update = True
else:
    update = False

if not os.path.exists(data_dir):
    os.makedirs(data_dir)

db = SqliteQueueDatabase(os.path.join(data_dir, "cozy.db"), pragmas=[('journal_mode', 'wal')])

class ModelBase(Model):
    class Meta:
        database = db


def get_db():
    global db
    return db


def get_data_dir():
    global data_dir
    return data_dir


def get_update():
    global update
    return update
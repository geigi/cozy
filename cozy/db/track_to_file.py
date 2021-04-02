from peewee import ForeignKeyField, IntegerField

from cozy.db.file import File
from cozy.db.model_base import ModelBase
from cozy.db.track import Track


class TrackToFile(ModelBase):
    track = ForeignKeyField(Track)
    file = ForeignKeyField(File)
    start_at = IntegerField()

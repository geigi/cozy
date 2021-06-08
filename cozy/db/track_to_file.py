from peewee import ForeignKeyField, IntegerField

from cozy.db.file import File
from cozy.db.model_base import ModelBase
from cozy.db.track import Track


class TrackToFile(ModelBase):
    track = ForeignKeyField(Track, unique=True, backref='track_to_file')
    file = ForeignKeyField(File, unique=False)
    start_at = IntegerField()

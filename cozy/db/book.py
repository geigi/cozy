from peewee import BlobField, BooleanField, CharField, FloatField, IntegerField

from cozy.db.model_base import ModelBase


class Book(ModelBase):
    name = CharField()
    author = CharField()
    reader = CharField()
    position = IntegerField()
    rating = IntegerField()
    cover = BlobField(null=True)
    playback_speed = FloatField(default=1.0)
    last_played = IntegerField(default=0)
    offline = BooleanField(default=False)
    downloaded = BooleanField(default=False)

from cozy.model.model_base import ModelBase
from peewee import CharField, IntegerField, BlobField, FloatField, BooleanField


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

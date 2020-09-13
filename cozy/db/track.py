from peewee import CharField, IntegerField, ForeignKeyField, FloatField

from cozy.db.model_base import ModelBase
from cozy.db.book import Book


class Track(ModelBase):
    name = CharField()
    number = IntegerField()
    disk = IntegerField()
    position = IntegerField()
    book = ForeignKeyField(Book)
    file = CharField()
    length = FloatField()
    modified = IntegerField()

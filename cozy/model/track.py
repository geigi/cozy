from peewee import CharField, IntegerField, ForeignKeyField, FloatField

from cozy.model.model_base import ModelBase
from cozy.model.book import Book


class Track(ModelBase):
    name = CharField()
    number = IntegerField()
    disk = IntegerField()
    position = IntegerField()
    book = ForeignKeyField(Book)
    file = CharField()
    length = FloatField()
    modified = IntegerField()

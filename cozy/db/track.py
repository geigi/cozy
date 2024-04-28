from peewee import CharField, FloatField, ForeignKeyField, IntegerField

from cozy.db.book import Book
from cozy.db.model_base import ModelBase


class Track(ModelBase):
    name = CharField()
    number = IntegerField()
    disk = IntegerField()
    position = IntegerField()
    book = ForeignKeyField(Book)
    length = FloatField()

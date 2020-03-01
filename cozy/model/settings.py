from peewee import CharField, BooleanField, ForeignKeyField, IntegerField

from cozy.model.model_base import ModelBase
from cozy.model.book import Book

DB_VERSION = 8


class Settings(ModelBase):
    path = CharField()
    first_start = BooleanField(default=True)
    last_played_book = ForeignKeyField(Book, null=True)
    version = IntegerField(default=DB_VERSION)

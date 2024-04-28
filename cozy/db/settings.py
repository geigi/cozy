from peewee import BooleanField, CharField, ForeignKeyField, IntegerField

from cozy.db.book import Book
from cozy.db.model_base import ModelBase

DB_VERSION = 10


class Settings(ModelBase):
    path = CharField()
    first_start = BooleanField(default=True)
    last_played_book = ForeignKeyField(Book, null=True)
    version = IntegerField(default=DB_VERSION)

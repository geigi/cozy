import os
from peewee import *
from xdg import *

data_dir = BaseDirectory.xdg_data_home + "/cozy/"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

db = SqliteDatabase(data_dir + "cozy.db")

class BaseModel(Model):
  class Meta:
    database = db

class Book(BaseModel):
  name = CharField()
  author = CharField()
  reader = CharField()
  position = IntegerField()
  rating = IntegerField()

class Track(BaseModel):
  name = CharField()
  length = IntegerField()
  number = IntegerField()
  position = IntegerField()
  book = ForeignKeyField(Book)
  file = CharField()

db.connect()
# Create tables only when not already present
#                               |
db.create_tables([Track, Book], True)

def Books():
  return Book.select()

def Search(search):
  return Track.select().where(search in Track.name)

def Tracks(book):
  return Track.select().where(book == Track.book)
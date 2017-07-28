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
  cover = BlobField(null=True)

class Track(BaseModel):
  name = CharField()
  number = IntegerField()
  position = IntegerField()
  book = ForeignKeyField(Book)
  file = CharField()

class Settings(BaseModel):
  path = CharField()

db.connect()
# Create tables only when not already present
#                               |
db.create_tables([Track, Book, Settings], True)

if (Settings.select().count() < 1):
  print("Init default audio book location path")
  home_dir = path = os.path.expanduser('~') + "/AudioBooks"
  if not os.path.exists(home_dir):
    os.makedirs(home_dir)

  Settings.create(path = home_dir)

def Books():
  return Book.select()

def Search(search):
  return Track.select().where(search in Track.name)

def Tracks(book):
  return Track.select().where(book == Track.book)

def CleanDB():
  pass
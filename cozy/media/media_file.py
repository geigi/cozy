from typing import List

from cozy.media.chapter import Chapter


class MediaFile:
    book_name: str
    author: str
    reader: str
    disk: int
    track_number: int
    length: float
    cover: bytes
    uri: str
    modified: int
    chapters: List[Chapter]

    def __init__(self, book_name: str, author: str, reader: str, disk: int, track_number: int, length: float,
                 cover: bytes, uri: str, modified: int, chapters: List[Chapter]):
        self.book_name = book_name
        self.author = author
        self.reader = reader
        self.disk = disk
        self.track_number = track_number
        self.length = length
        self.cover = cover
        self.uri = uri
        self.modified = modified
        self.chapters = chapters

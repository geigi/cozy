from typing import List

from cozy.media.chapter import Chapter


class MediaFile:
    book_name: str
    author: str
    reader: str
    disk: int
    cover: bytes
    path: str
    modified: int
    chapters: List[Chapter]

    def __init__(self, book_name: str, author: str, reader: str, disk: int, cover: bytes, path: str, modified: int,
                 chapters: List[Chapter]):
        self.book_name = book_name
        self.author = author
        self.reader = reader
        self.disk = disk
        self.cover = cover
        self.path = path
        self.modified = modified
        self.chapters = chapters

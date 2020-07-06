from dataclasses import dataclass
from typing import List

from cozy.media.chapter import Chapter


@dataclass
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

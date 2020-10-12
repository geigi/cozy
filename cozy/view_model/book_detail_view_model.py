from typing import Optional

from cozy import tools
from cozy.architecture.event_sender import EventSender
from cozy.architecture.observable import Observable
from cozy.ext import inject
from cozy.media.player import Player
from cozy.model.book import Book
from cozy.model.chapter import Chapter


class BookDetailViewModel(Observable, EventSender):
    _player: Player = inject.attr(Player)

    def __init__(self):
        super().__init__()
        super(Observable, self).__init__()

        self._player.add_listener(self._on_player_event)

    @property
    def play(self) -> bool:
        return self._play

    @play.setter
    def play(self, value: bool):
        self._play = value
        self._notify("play")

    @property
    def current_chapter(self) -> Optional[Chapter]:
        return self.current_chapter

    @current_chapter.setter
    def current_chapter(self, value: Chapter):
        self._current_chapter = value
        self._notify("current_chapter")

    @property
    def book(self) -> Optional[Book]:
        return self._book

    @book.setter
    def book(self, value: Book):
        self._book = value
        self._notify("book")

    @property
    def last_played_text(self) -> Optional[str]:
        if not self._book:
            return None

        return tools.past_date_to_human_readable(self._book.last_played)

    @property
    def disk_count(self) -> int:
        if not self._book:
            return 0

        return len({chapter.disk
                    for chapter
                    in self._book.chapters})

    def _on_player_event(self, event, message):
        if event == "play":
            track_id = message
            book = None

            for b in self._model.books:
                if any(chapter.id == track_id for chapter in b.chapters):
                    book = b
                    break

            if book:
                book.reload()
                self._notify("book")

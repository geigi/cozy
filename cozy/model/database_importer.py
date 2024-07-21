import logging

import inject
from peewee import SqliteDatabase, fn

from cozy.db.book import Book as BookModel
from cozy.db.file import File
from cozy.db.track import Track
from cozy.db.track_to_file import TrackToFile
from cozy.extensions.is_same_book import is_same_book
from cozy.media.media_file import MediaFile
from cozy.model.book import Book, BookIsEmpty

log = logging.getLogger("db_importer")


class TrackInsertRequest:
    track_data: object
    file: File
    start_at: int

    def __init__(self, track_data: object, file: File, start_at: int):
        self.track_data = track_data
        self.file = file
        self.start_at = start_at


class BookUpdatePositionRequest:
    book_id: int
    progress: int

    def __init__(self, book_id: int, progress: int):
        self.book_id = book_id
        self.progress = progress


class DatabaseImporter:
    _db = inject.attr(SqliteDatabase)

    def __init__(self):
        self._book_update_positions: list[BookUpdatePositionRequest] = []

    def insert_many(self, media_files: set[MediaFile]):
        self._book_update_positions = []

        files = self._prepare_files_db_objects(media_files)
        File.insert_many(files).execute()
        tracks = self._prepare_track_db_objects(media_files)
        self._insert_tracks(tracks)
        self._update_book_positions()

    def _prepare_files_db_objects(self, media_files: set[MediaFile]) -> list[object]:
        files = []

        for media_file in media_files:
            query = File.select().where(File.path == media_file.path)

            if query.exists():
                self._update_files_in_db(query.get(), media_file)
                continue

            file_already_in_list = any(f["path"] == media_file.path for f in files)

            if not file_already_in_list:
                files.append({"path": media_file.path, "modified": media_file.modified})

        return files

    def _update_files_in_db(self, file: File, media_file: MediaFile):
        file.modified = media_file.modified
        file.save(only=file.dirty_fields)

    def _prepare_track_db_objects(self, media_files: set[MediaFile]) -> set[TrackInsertRequest]:
        book_db_objects: set[BookModel] = set()

        for media_file in media_files:
            if not media_file:
                continue

            book = next((book for book in book_db_objects if is_same_book(book.name, media_file.book_name)), None)
            file_query = File.select().where(File.path == media_file.path)
            if not file_query.exists():
                log.error("No file object with path present: %s", media_file.path)
                continue

            file = file_query.get()

            if not book:
                book = self._import_or_update_book(media_file)
                book_db_objects.add(book)

            try:
                book_model = Book(self._db, book)
                progress = book_model.progress
            except BookIsEmpty:
                progress = 0

            self._delete_tracks_from_db(media_file)
            tracks = self._get_track_list_for_db(media_file, book)

            for track in tracks:
                start_at = track.pop("startAt")
                yield TrackInsertRequest(track, file, start_at)

            update_position_request_present = any(b.book_id == book.id for b in self._book_update_positions)
            if progress > 0 and not update_position_request_present:
                self._book_update_positions.append(BookUpdatePositionRequest(book.id, progress))

    def _import_or_update_book(self, media_file):
        if BookModel.select(BookModel.name).where(self._matches_db_book(media_file.book_name)).count() < 1:
            book = self._create_book_db_object(media_file)
        else:
            book = self._update_book_db_object(media_file)
        return book

    def _matches_db_book(self, book_name: str) -> bool:
        return fn.Lower(BookModel.name) == book_name.lower()

    def _get_track_list_for_db(self, media_file: MediaFile, book: BookModel):
        tracks = []

        for chapter in media_file.chapters:
            tracks.append({
                "name": chapter.name,
                "number": chapter.number,
                "disk": media_file.disk,
                "book": book,
                "length": chapter.length,
                "startAt": chapter.position,
                "position": 0
            })

        return tracks

    def _update_book_db_object(self, media_file: MediaFile) -> BookModel:
        BookModel.update(name=media_file.book_name,
                         author=media_file.author,
                         reader=media_file.reader,
                         cover=media_file.cover) \
            .where(self._matches_db_book(media_file.book_name)) \
            .execute()
        return BookModel.select().where(self._matches_db_book(media_file.book_name)).get()

    def _create_book_db_object(self, media_file: MediaFile) -> BookModel:
        return BookModel.create(name=media_file.book_name,
                                author=media_file.author,
                                reader=media_file.reader,
                                cover=media_file.cover,
                                position=0,
                                rating=-1)

    def _get_track_db_objects_for_media_file(self, media_file: MediaFile) -> list[Track]:
        all_track_mappings = TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path)

        for item in all_track_mappings:
            yield item.track

    def _delete_tracks_from_db(self, media_file: MediaFile):
        for track in self._get_track_db_objects_for_media_file(media_file):
            track.delete_instance(recursive=True)

    def _is_chapter_count_in_db_different(self, media_file: MediaFile) -> bool:
        all_track_mappings = self._get_chapter_count_in_db(media_file)

        return all_track_mappings != len(media_file.chapters)

    def _get_chapter_count_in_db(self, media_file: MediaFile) -> int:
        all_track_mappings = TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path)

        return all_track_mappings.count()

    def _insert_tracks(self, tracks: set[TrackInsertRequest]):
        for track in tracks:
            track_db = Track.insert(track.track_data).execute()
            TrackToFile.create(track=track_db, file=track.file, start_at=track.start_at)

    def _update_book_positions(self):
        for book_position in self._book_update_positions:
            book = BookModel.get_or_none(book_position.book_id)

            if not book:
                log.error("Could not restore book position because book is not present")
                continue

            self._update_book_position(book, book_position.progress)

        self._book_update_positions = []

    def _update_book_position(self, book: BookModel, progress: int):
        try:
            book_model = Book(self._db, book)
        except BookIsEmpty:
            log.error("Could not restore book position because book is empty")
            return

        completed_chapter_length = 0
        for chapter in book_model.chapters:
            old_position = progress
            if completed_chapter_length + chapter.length > old_position:
                chapter.position = chapter.start_position + (old_position - completed_chapter_length)
                book_model.position = chapter.id
                return
            else:
                completed_chapter_length += chapter.length

        book_model.position = 0

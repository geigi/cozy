import logging
from typing import List, Set, Tuple

from cozy.db.book import Book as BookModel
from cozy.db.file import File
from cozy.db.track import Track
from cozy.db.track_to_file import TrackToFile
from cozy.media.media_file import MediaFile


log = logging.getLogger("db_importer")


class TrackInsertRequest:
    track_data: object
    file: File
    start_at: int

    def __init__(self, track_data: object, file: File, start_at: int):
        self.track_data = track_data
        self.file = file
        self.start_at = start_at


class DatabaseImporter:
    def insert_many(self, media_files: Set[MediaFile]):
        files = self._prepare_files_db_objects(media_files)
        File.insert_many(files).execute()
        tracks = self._prepare_track_db_objects(media_files)
        self._insert_tracks(tracks)

    def _prepare_files_db_objects(self, media_files: Set[MediaFile]) -> List[object]:
        files = []

        for media_file in media_files:
            query = File.select().where(File.path == media_file.path)

            if query.exists():
                self._update_files_in_db(query.get(), media_file)
                continue

            files.append({"path": media_file.path, "modified": media_file.modified})

        return files

    def _update_files_in_db(self, file: File, media_file: MediaFile):
        file.modified = media_file.modified
        file.save(only=file.dirty_fields)

    def _prepare_track_db_objects(self, media_files: Set[MediaFile]) -> Set[TrackInsertRequest]:
        book_db_objects: Set[BookModel] = set()

        for media_file in media_files:
            if not media_file:
                continue

            book = next((book for book in book_db_objects if book.name == media_file.book_name), None)
            file_query = File.select().where(File.path == media_file.path)
            if not file_query.exists():
                log.error("No file object with path present: {}".format(media_file.path))
                continue

            file = file_query.get()

            if not book:
                book = self._import_or_update_book(media_file)
                book_db_objects.add(book)

            if self._is_chapter_count_in_db_different(media_file):
                self._delete_tracks_from_db(media_file)
                tracks = self._get_track_list_for_db(media_file, book)

                for track in tracks:
                    start_at = track.pop("startAt")
                    yield TrackInsertRequest(track, file, start_at)
            else:
                self._update_track_db_object(media_file, book)

    def _import_or_update_book(self, media_file):
        if BookModel.select(BookModel.name).where(BookModel.name == media_file.book_name).count() < 1:
            book = self._create_book_db_object(media_file)
        else:
            book = self._update_book_db_object(media_file)
        return book

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

    def _update_track_db_object(self, media_file: MediaFile, book: BookModel):
        all_track_mappings = [item.track
                              for item
                              in TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path)]

        for chapter in media_file.chapters:
            Track \
                .update(name=chapter.name,
                        number=chapter.number,
                        book=book,
                        disk=media_file.disk,
                        length=chapter.length) \
                .where(Track.id << all_track_mappings) \
                .execute()

    def _update_book_db_object(self, media_file: MediaFile) -> BookModel:
        BookModel.update(name=media_file.book_name,
                         author=media_file.author,
                         reader=media_file.reader,
                         cover=media_file.cover) \
            .where(BookModel.name == media_file.book_name) \
            .execute()
        return BookModel.select().where(BookModel.name == media_file.book_name).get()

    def _create_book_db_object(self, media_file: MediaFile) -> BookModel:
        return BookModel.create(name=media_file.book_name,
                                author=media_file.author,
                                reader=media_file.reader,
                                cover=media_file.cover,
                                position=0,
                                rating=-1)

    def _get_track_db_objects_for_media_file(self, media_file: MediaFile) -> List[Track]:
        all_track_mappings = TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path)

        for item in all_track_mappings:
            yield item.track

    def _delete_tracks_from_db(self, media_file: MediaFile):
        for track in self._get_track_db_objects_for_media_file(media_file):
            track.delete_instance(recursive=True)

    def _is_chapter_count_in_db_different(self, media_file: MediaFile) -> bool:
        all_track_mappings = TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path)

        if all_track_mappings.count() != len(media_file.chapters):
            return True
        else:
            return False

    def _insert_tracks(self, tracks: Set[TrackInsertRequest]):
        for track in tracks:
            track_db = Track.insert(track.track_data).execute()
            TrackToFile.create(track=track_db, file=track.file, start_at=track.start_at)

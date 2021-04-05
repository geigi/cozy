from typing import List, Set

from cozy.db.book import Book as BookModel
from cozy.db.file import File
from cozy.db.track import Track
from cozy.db.track_to_file import TrackToFile
from cozy.media.media_file import MediaFile


class DatabaseImporter:
    def insert_many(self, media_files: Set[MediaFile]):
        files = self._prepare_files_db_objects(media_files)
        File.insert_many(files).execute()
        tracks = self._prepare_track_db_objects(media_files)
        Track.insert_many(tracks).execute()

    def _prepare_files_db_objects(self, media_files: Set[MediaFile]) -> List[object]:
        files = []

        for media_file in media_files:
            query = File.select().where(File.path == media_file.path)

            if query.exists():
                continue

            files.append({"path": media_file.path})

        return files

    def _prepare_track_db_objects(self, media_files: Set[MediaFile]) -> Set[object]:
        book_db_objects: Set[BookModel] = set()

        for media_file in media_files:
            if not media_file:
                continue

            book = next((book for book in book_db_objects if book.name == media_file.book_name), None)
            file = self._get_file_db_object(media_file.path)

            if not book:
                book = self._import_or_update_book(media_file)
                book_db_objects.add(book)

            if self._is_chapter_count_in_db_different(media_file):
                self._delete_tracks_from_db(media_file)
                tracks = self._get_track_list_for_db(media_file, book)

                for track in tracks:
                    yield track
            else:
                self._update_track_db_object(media_file, book)

    def _get_file_db_object(self, path: str) -> File:
        query = File.select(File.path == path)

        if query.exists():
            return query.get()
        else:
            return File.create(path=path)

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
                "number": media_file.track_number,
                "disk": media_file.disk,
                "book": book,
                "length": media_file.length,
                "modified": media_file.modified,
                "position": media_file.chapters[0].position
            })

        return tracks

    def _update_track_db_object(self, media_file: MediaFile, book: BookModel):
        all_track_mappings = [item.track
                              for item
                              in TrackToFile.select().join(File).where(TrackToFile.file.path == media_file.path)]

        for chapter in media_file.chapters:
            Track \
                .update(name=chapter.name,
                        number=media_file.track_number,
                        book=book,
                        disk=media_file.disk,
                        length=media_file.length,
                        modified=media_file.modified) \
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

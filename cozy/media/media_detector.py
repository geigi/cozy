import logging
import pathlib

from cozy.architecture.event_sender import EventSender

from cozy.media.media_file import MediaFile
from cozy.media.tag_reader import TagReader

from gi.repository import Gst, GstPbutils

log = logging.getLogger("media_detector")


class NotAnAudioFile(Exception):
    pass


class AudioFileCouldNotBeDiscovered(Exception):
    pass


class MediaDetector(EventSender):
    def __init__(self, path: str):
        super().__init__()
        self.uri = pathlib.Path(path).as_uri()

        Gst.init(None)
        self.discoverer: GstPbutils.Discoverer = GstPbutils.Discoverer()

    def get_media_data(self) -> MediaFile:
        if not self._has_audio_file_ending():
            raise NotAnAudioFile

        try:
            discoverer_info: GstPbutils.DiscovererInfo = self.discoverer.discover_uri(self.uri)
        except Exception:
            log.info("Skipping file because it couldn't be detected: %s", self.uri)
            raise AudioFileCouldNotBeDiscovered(self.uri) from None

        is_valid_audio_file = self._is_valid_audio_file(discoverer_info)
        if is_valid_audio_file:
            tag_reader = TagReader(self.uri, discoverer_info)
            tags = tag_reader.get_tags()
            return tags
        else:
            raise AudioFileCouldNotBeDiscovered(self.uri)

    def _is_valid_audio_file(self, discoverer_info: GstPbutils.DiscovererInfo):
        audio_streams = discoverer_info.get_audio_streams()
        video_streams = discoverer_info.get_video_streams()

        if len(audio_streams) < 1:
            log.info("File contains no audio stream.")
            return False
        elif len(audio_streams) > 1:
            log.info("File contains more than one audio stream.")
            return False
        elif len(video_streams) > 0:
            log.info("File contains a video stream.")
            return False

        return True

    def _has_audio_file_ending(self) -> bool:
        return self.uri.lower().endswith(('.mp3', '.ogg', '.flac', '.m4a', '.m4b', '.mp4', '.wav', '.opus'))

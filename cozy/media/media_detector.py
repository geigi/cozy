import logging
import pathlib

from gi.repository import Gst, GstPbutils

from cozy.architecture.event_sender import EventSender
from cozy.media.media_file import MediaFile
from cozy.media.tag_reader import TagReader

log = logging.getLogger(__name__)


class NotAnAudioFile(Exception):
    pass


class AudioFileCouldNotBeDiscovered(Exception):
    pass


class MediaDetector(EventSender):
    def __init__(self, path: str):
        super().__init__()
        self.uri = pathlib.Path(path).absolute().as_uri()

        Gst.init(None)
        self.discoverer: GstPbutils.Discoverer = GstPbutils.Discoverer()

    def get_media_data(self) -> MediaFile:
        try:
            discoverer_info = self.discoverer.discover_uri(self.uri)
        except Exception:
            log.info("Skipping file because it couldn't be detected: %s", self.uri)
            raise AudioFileCouldNotBeDiscovered(self.uri) from None

        if self._is_valid_audio_file(discoverer_info):
            return TagReader(self.uri, discoverer_info).get_tags()
        else:
            raise AudioFileCouldNotBeDiscovered(self.uri)

    def _is_valid_audio_file(self, info: GstPbutils.DiscovererInfo):
        return len(info.get_audio_streams()) == 1 and not info.get_video_streams()

import logging
import pathlib

from cozy.architecture.event_sender import EventSender

import gi

from cozy.media.media_file import MediaFile
from cozy.media.tag_reader import TagReader

gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
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
        if not self.uri.endswith(('.mp3', '.ogg', '.flac', '.m4a', '.m4b', '.wav', '.opus')):
            raise NotAnAudioFile

        try:
            discoverer_info: GstPbutils.DiscovererInfo = self.discoverer.discover_uri(self.uri)
        except Exception as e:
            log.info("Skipping file because it couldn't be detected: {}".format(self.uri))
            raise AudioFileCouldNotBeDiscovered(self.uri)

        if self._is_valid_audio_file(discoverer_info):
            tag_reader = TagReader(self.uri, discoverer_info)
            return tag_reader.get_tags()
        else:
            raise AudioFileCouldNotBeDiscovered(self.uri)

    def _is_valid_audio_file(self, discoverer_info: GstPbutils.DiscovererInfo):
        audio_streams = discoverer_info.get_audio_streams()

        if len(audio_streams) < 1:
            print("File contains no audio stream.")
            return False
        elif len(audio_streams) > 1:
            print("File contains more than one audio stream.")
            return False

        return True

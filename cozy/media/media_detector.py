import logging
import pathlib

from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton

import gi

from cozy.media.media_file import MediaFile
from cozy.media.tag_reader import TagReader

gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst, GstPbutils


log = logging.getLogger("media_detector")


class NotAnAudioFile(Exception):
    pass


class MediaDetector(EventSender, metaclass=Singleton):
    def __init__(self, path: str):
        self.uri = pathlib.Path(path).as_uri()

        Gst.init(None)
        self.discoverer: GstPbutils.Discoverer = GstPbutils.Discoverer()

    def get_media_data(self) -> MediaFile:
        try:
            discoverer_info: GstPbutils.DiscovererInfo = self.discoverer.discover_uri(self.uri)
        except Exception as e:
            log.info("Skipping file because it couldn't be detected: {}".format(self.uri))
            raise NotAnAudioFile

        if self._is_valid_audio_file(discoverer_info):
            tag_reader = TagReader(self.uri, discoverer_info)
            return tag_reader.get_tags()
        else:
            raise NotAnAudioFile

    def _is_valid_audio_file(self, discoverer_info: GstPbutils.DiscovererInfo):
        if not self.uri.endswith(('.mp3', '.ogg', '.flac', '.m4a', '.wav', '.opus')):
            return False

        audio_streams = discoverer_info.get_audio_streams()

        if len(audio_streams) < 1:
            print("File contains no audio stream.")
            return False
        elif len(audio_streams) > 1:
            print("File contains more than one audio stream.")
            return False

        return True

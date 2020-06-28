from cozy.architecture.event_sender import EventSender
from cozy.architecture.singleton import Singleton

import gi

gi.require_version('GstPbutils', '1.0')
from gi.repository import GstPbutils, Gst


class media_detector(EventSender, metaclass=Singleton):
    def __init__(self):
        self.discoverer: GstPbutils.Discoverer = GstPbutils.Discoverer()

    def _import_file(self, uri):
        discoverer_info: GstPbutils.DiscovererInfo = self.discoverer.discover_uri(uri)

        if self._is_valid_audio_file(discoverer_info):
            tags = self._get_tags(discoverer_info)

    def _is_valid_audio_file(self, discoverer_info: GstPbutils.DiscovererInfo):
        audio_streams = discoverer_info.get_audio_streams()

        if len(audio_streams < 1):
            print("File contains no audio stream.")
            return False
        elif len(audio_streams) > 1:
            print("File contains more than one audio stream.")
            return False

        return True

    def _get_tags(self, discoverer_info: GstPbutils.DiscovererInfo):
        tags: Gst.TagList = discoverer_info.get_tags()
        return []
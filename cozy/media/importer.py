import os
from enum import Enum, auto

from cozy.architecture.event_sender import EventSender
from cozy.model.library import Library


class ScanStatus(Enum):
    STARTED = auto()
    SUCCESS = auto()
    ABORTED = auto()
    FINISHED_WITH_ERRORS = auto()


class Importer(EventSender):
    def __init__(self, library: Library):
        self._library = library

    def scan(self):
        self.emit_event("scan", ScanStatus.STARTED)



    def _get_file_count_in_dir(self, dir):
        len([name for name in os.listdir(dir) if os.path.isfile(name)])

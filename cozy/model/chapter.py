from abc import ABC, abstractmethod

from cozy.architecture.event_sender import EventSender


class Chapter(ABC, EventSender):
    id: int

    def __init__(self):
        super().__init__()
        super(ABC, self).__init__()

    @property
    @abstractmethod
    def name(self):
        pass

    @name.setter
    @abstractmethod
    def name(self, new_name: str):
        pass

    @property
    @abstractmethod
    def number(self):
        pass

    @number.setter
    @abstractmethod
    def number(self, new_number: int):
        pass

    @property
    @abstractmethod
    def disk(self):
        pass

    @disk.setter
    @abstractmethod
    def disk(self, new_disk: int):
        pass

    @property
    @abstractmethod
    def position(self):
        pass

    @position.setter
    @abstractmethod
    def position(self, new_position: int):
        pass

    @property
    @abstractmethod
    def file(self) -> str:
        pass

    @file.setter
    @abstractmethod
    def file(self, new_file: str):
        pass

    @property
    @abstractmethod
    def length(self):
        pass

    @length.setter
    @abstractmethod
    def length(self, new_length: float):
        pass

    @property
    @abstractmethod
    def modified(self):
        pass

    @modified.setter
    @abstractmethod
    def modified(self, new_modified: int):
        pass

    @abstractmethod
    def delete(self):
        pass
from dataclasses import dataclass

@dataclass
class Chapter:
    name: str | None
    position: int | None  # in nanoseconds
    length: float | None  # in seconds... sigh  # FIXME: finally use nanoseconds everywhere consistently
    number: int | None

    def is_valid(self):
        return self.name is not None and self.position is not None

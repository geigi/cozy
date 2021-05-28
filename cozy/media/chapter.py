class Chapter:
    name: str
    position: int
    length: float
    number: int

    def __init__(self, name: str, position: int, length: float, number: int):
        self.name = name
        self.position = position
        self.number = number
        self.length = length

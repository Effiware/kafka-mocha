from enum import Enum


class Tick:
    DONE = -1

    def __init__(self, interval: int):
        if interval <= 0:
            raise ValueError("Tick interval must be an unsigned integer.")
        self.interval = interval


class KSignals(Enum):
    INIT = None
    SUCCESS = "SUCCESS"
    BUFFERED = "BUFFERED"
    FAILURE = "FAILURE"

    def __str__(self) -> str:
        return str(self.value)

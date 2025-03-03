from enum import Enum


class Tick:
    DONE = -1

    def __init__(self, interval_ms: int):
        if not isinstance(interval_ms, int) or interval_ms <= 0:
            raise ValueError("Tick interval must be an unsigned integer.")
        self.interval_ms = interval_ms


class KSignals(Enum):
    INIT = None
    SUCCESS = "SUCCESS"
    BUFFERED = "BUFFERED"
    FAILURE = "FAILURE"

    def __str__(self) -> str:
        return str(self.value)


class KMarkers(Enum):
    COMMIT = "COMMIT"
    ABORT = "ABORT"

    def __str__(self) -> str:
        return str(self.value)

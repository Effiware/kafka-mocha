from threading import Thread, Event
from time import sleep

from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.signals import Tick

logger = get_custom_logger()


class TickingThread(Thread):
    def __init__(self, owner: str, message_buffer, tick_interval=5):
        Thread.__init__(self)
        self._owner = owner
        self._message_buffer = message_buffer
        self._tick = Tick(tick_interval)
        self._stop_event = Event()
        logger.info(f"Buffer for {self._owner}: ticking initialized")

    def run(self) -> None:
        logger.info(f"Buffer for {self._owner}: ticking started")

        while not self._stop_event.is_set():
            logger.debug(f"Buffer for {self._owner}: tick (+{self._tick.interval})...")
            # self._message_buffer.send(self._tick.interval)  # TODO: Check if not running first
            sleep(self._tick.interval)
        self._message_buffer.send(Tick.DONE)

    def stop(self) -> None:
        logger.info(f"Buffer for {self._owner}: stop event")
        self._stop_event.set()

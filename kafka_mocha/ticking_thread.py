from inspect import GEN_SUSPENDED, getgeneratorstate
from threading import Event, Thread
from time import sleep

from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.signals import Tick

logger = get_custom_logger()


class TickingThread(Thread):
    def __init__(self, owner: str, message_buffer, tick_interval=0.1):
        Thread.__init__(self)
        self._owner = owner
        self._message_buffer = message_buffer
        self._tick = Tick(tick_interval)
        self._stop_event = Event()
        logger.info("Buffer for %s: ticking initialized", self._owner)

    def run(self) -> None:
        logger.info("Buffer for %s: ticking started", self._owner)
        sleep(self._tick.interval)

        while not self._stop_event.is_set():
            if getgeneratorstate(self._message_buffer) == GEN_SUSPENDED:
                logger.debug("Buffer for %s: tick (+%.3fs)...", self._owner, self._tick.interval)
                self._message_buffer.send(self._tick.interval)
            sleep(self._tick.interval)
        sleep(self._tick.interval * 3)  # TODO: make it better
        self._message_buffer.send(Tick.DONE)

    def stop(self) -> None:
        logger.info("Buffer for %s: stop event", self._owner)
        self._stop_event.set()

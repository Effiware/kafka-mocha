from inspect import GEN_SUSPENDED, getgeneratorstate
from threading import Event, Thread
from time import sleep

from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.signals import Tick

logger = get_custom_logger()


class TickingThread(Thread):
    """Thread that sends ticks to the message buffer. It is used to control the message buffer's flow."""

    def __init__(self, owner: str, message_buffer, tick_interval_ms=100):
        """Initialize the ticking thread.

        :param owner: KProducer's id that owns the message buffer.
        :param message_buffer: Buffer (python generator) that owns the ticking thread (should receive ticks from it).
        :param tick_interval_ms: Interval between ticks in milliseconds.
        """
        Thread.__init__(self, name=f"{owner}_ticking_thread")
        self._owner = owner
        self._message_buffer = message_buffer
        self._tick = Tick(tick_interval_ms)
        self._stop_event = Event()
        logger.info("Buffer for %s: ticking initialized", self._owner)

    def _sleep(self, amplifier: int = 1) -> None:
        """Sleep for the tick interval multiplied by the amplifier."""
        sleep(self._tick.interval_ms * amplifier / 1000)

    def run(self) -> None:
        logger.info("Buffer for %s: ticking started", self._owner)
        self._sleep()

        while not self._stop_event.is_set():
            if getgeneratorstate(self._message_buffer) == GEN_SUSPENDED:
                logger.debug("Buffer for %s: tick (+%.0fms)...", self._owner, self._tick.interval_ms)
                self._message_buffer.send(self._tick.interval_ms)
            self._sleep()
        self._sleep(3)  # TODO: Properly handle the last tick, it should be sent after the buffer is done
        self._message_buffer.send(Tick.DONE)

    def stop(self) -> None:
        logger.info("Buffer for %s: stop event", self._owner)
        self._stop_event.set()

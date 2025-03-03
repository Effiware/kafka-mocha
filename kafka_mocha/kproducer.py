import signal
from inspect import GEN_SUSPENDED, getgeneratorstate
from time import sleep, time
from typing import Any, Literal, Optional

from confluent_kafka import KafkaException, TopicPartition

from kafka_mocha.buffer_handler import buffer_handler
from kafka_mocha.exceptions import KProducerMaxRetryException, KProducerTimeoutException
from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import PMessage
from kafka_mocha.signals import KMarkers, KSignals, Tick
from kafka_mocha.ticking_thread import TickingThread
from kafka_mocha.utils import validate_config

MAX_BUFFER_LEN = 2147483647


class KProducer:
    """
    Confluent Kafka Producer mockup. It is used to simulate and fully imitate Kafka Producer behaviour. It is
    implemented as a generator function that is controlled by a TickingThread (automatic message flush for given "time"
    intervals). It is used to send messages to Kafka Simulator and can be safely used in integration tests or as an
    emulator for Kafka Producer.
    """

    def __init__(
        self,
        config: dict[str, Any],
        output: Optional[dict[str, Any]] = None,
        loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING",
    ):
        validate_config("producer", config)
        self.config = config
        self.output = output
        self.logger = get_custom_logger(loglevel)
        self._transactional_id = config.get("transactional.id")
        self._max_retry_count = config.get("retries", config.get("message.send.max.retries", 6))
        self._retry_backoff = config.get("retry.backoff.ms", 10) / 1000  # in seconds

        self.buffer = []
        buffer_len = config.get("queue.buffering.max.messages", 5)
        buffer_len = MAX_BUFFER_LEN if buffer_len == 0 else buffer_len
        buffer_max_ms = config.get("linger.ms", config.get("queue.buffering.max.ms", 300))
        self._buffer_handler = buffer_handler(
            f"KProducer({id(self)})",
            self.buffer,
            buffer_len,
            buffer_max_ms,
            transact=self._transactional_id is not None,
        )

        self._ticking_thread = TickingThread(f"KProducer({id(self)})", self._buffer_handler)
        self._buffer_handler.send(KSignals.INIT.value)
        self._kafka_simulator = KafkaSimulator()
        self._ticking_thread.start()

        self.transaction_inited = False
        self.transaction_begun = False

    def abort_transaction(self):
        if not self.transaction_begun:
            raise KafkaException("{code=_STATE,val=-172,str='Unable to produce message: Local: Erroneous state'}")

        self.purge()
        self._kafka_simulator.transaction_coordinator("abort", id(self), self._transactional_id)
        key = str({"transactionalId": self._transactional_id, "markerType": KMarkers.ABORT.value})
        value = str({"producerId": id(self), "markerType": KMarkers.ABORT.value})
        message = PMessage("buffer", 666, key.encode(), value.encode(), timestamp=0, marker=True)
        self._send_with_retry(message)
        self.transaction_begun = False

    def begin_transaction(self):
        if not self.transaction_inited:
            raise KafkaException("{code=_STATE,val=-172,str='Unable to produce message: Local: Erroneous state'}")

        self._kafka_simulator.transaction_coordinator("begin", id(self), self._transactional_id)
        self.transaction_begun = True

    def commit_transaction(self):
        if not self.transaction_begun:
            raise KafkaException("{code=_STATE,val=-172,str='Unable to produce message: Local: Erroneous state'}")

        self.flush()
        self._kafka_simulator.transaction_coordinator("commit", id(self), self._transactional_id)
        key = str({"transactionalId": self._transactional_id, "markerType": KMarkers.COMMIT.value})
        value = str({"producerId": id(self), "markerType": KMarkers.COMMIT.value})
        message = PMessage("buffer", 666, key.encode(), value.encode(), timestamp=0, marker=True)
        self._send_with_retry(message)
        self.transaction_begun = False

    def flush(self, timeout: Optional[float] = None):
        """Duck type for confluent_kafka/cimpl.py::flush (see signature there).

        Polls the producer (buffer_handler) as long as there are messages in the buffer.
        """
        start_buffer_len = len(self.buffer)
        while (buffer_len := len(self.buffer)) > 0:
            if timeout is not None:
                self._run_with_timeout_blocking(self._tick_buffer, timeout=timeout)
            else:
                self._tick_buffer()
        else:
            return start_buffer_len - buffer_len

    def init_transactions(self):
        if self._transactional_id is None:
            # TODO: Check if this is the correct
            raise KafkaException("{code=_STATE,val=-172,str='Unable to produce message: Local: Erroneous state'}")
        if self.transaction_inited:
            raise KafkaException("{code=_STATE,val=-172,str='Operation not valid in state Ready'}")

        self._kafka_simulator.transaction_coordinator("init", id(self), self._transactional_id)
        self.transaction_inited = True

    def list_topics(self, topic: str = None, timeout: float = -1.0, *args, **kwargs):
        """Duck type for confluent_kafka/cimpl.py::list_topics (see signature there).

        Returns ClusterMetadata object from Kafka Simulator.
        """
        if timeout != -1.0:
            self.logger.warning("KProducer doesn't support timing out for this method. Parameter will be ignored.")

        return self._kafka_simulator.get_cluster_mdata(topic)

    def poll(self, timeout: Optional[float] = None):
        """Duck type for confluent_kafka/cimpl.py::poll (see signature there).

        Polls the producer for events and calls the corresponding callbacks (if registered)
        """
        start_buffer_len = len(self.buffer)
        if timeout is not None:
            self._run_with_timeout_blocking(self._tick_buffer, timeout=timeout)
        else:
            self._tick_buffer()
        return start_buffer_len - len(self.buffer)

    def purge(self, *args, **kwargs):
        """Duck type for confluent_kafka/cimpl.py::purge (see signature there).

        Purges messages stored in internal message buffer.
        """
        self.buffer.clear()

    def produce(self, topic, value=None, key=None, partition=-1, on_delivery=None, timestamp=0, headers=None) -> None:
        """Duck type for confluent_kafka/cimpl.py::produce (see signature there).

        Instead of producing a real message to Kafka, it is sent to Kafka Simulator.
        """
        message = PMessage.from_producer_data(
            topic=topic,
            partition=partition,
            key=key,
            value=value,
            timestamp=timestamp,
            headers=headers,
            on_delivery=on_delivery,
        )
        self._send_with_retry(message)

    def send_offsets_to_transaction(
        self, positions: list[TopicPartition], group_metadata: object, timeout: float = None
    ):
        raise NotImplementedError("Transactions are not yet fully supported in Kafka Mocha.")

    def set_sasl_credentials(self, *args, **kwargs):
        raise NotImplementedError("Not yet implemented...")

    def _tick_buffer(self):
        """
        Sends `DONE` signal to message buffer handler in order to force sending buffered messages to Kafka Simulator.
        """
        try_count = 0
        while try_count < self._max_retry_count:
            if getgeneratorstate(self._buffer_handler) == GEN_SUSPENDED:
                self._buffer_handler.send(Tick.DONE)
                break
            else:
                try_count += 1
                sleep(try_count**2 * self._retry_backoff)
        else:
            raise KProducerMaxRetryException(f"Exceeded max send retries ({self._max_retry_count})")

    @staticmethod
    def _timeout_handler(signum: Any, frame: Any) -> None:
        """Handler for SIGALRM signal. Must be a staticmethod (otherwise GC may not collect it)."""
        raise KProducerTimeoutException("Timeout exceeded")

    def _run_with_timeout_blocking(self, func, args=(), kwargs={}, timeout: float = 5):
        """
        Run function with timeout and block if finished earlier, meaning:
            - raise TimeoutException if func doesn't end in the time specified
            - wait (block) if func ends earlier than specified time
        """
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout)
        start_time = time()
        try:
            result = func(*args, **kwargs)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed_time = time() - start_time
            remaining_time = timeout - elapsed_time
            if remaining_time > 0:
                sleep(remaining_time)
        return result

    def _send_with_retry(self, message: PMessage) -> None:
        """Send message to buffer handler with retry mechanism."""
        count = 0
        while count < self._max_retry_count:
            if getgeneratorstate(self._buffer_handler) == GEN_SUSPENDED:
                ack = self._buffer_handler.send(message)
                self.logger.debug("KProducer(%d): received ack: %s", id(self), ack)
                break
            else:
                self.logger.debug("KProducer(%d): buffer is busy", id(self))
                count += 1
                sleep(count**2 * self._retry_backoff)
        else:
            raise KProducerMaxRetryException(f"Exceeded max send retries ({self._max_retry_count})")

    def _done(self):
        """Additional method to gracefully close message buffer."""
        self._ticking_thread.stop()
        self._ticking_thread.join()
        self._buffer_handler.close()

    def __len__(self) -> int:
        return len(self.buffer)

    def __del__(self):
        if hasattr(self, "config"):  # if __init__ was called without exceptions
            if (curr_buff_len := len(self.buffer)) > 0:
                self.logger.warning(
                    "You may have a bug: Producer terminating with %d messages (%d bytes) still in queue or "
                    "transit: use flush() to wait for outstanding message delivery. "
                    "KProducer will flush them for you, but familiarize yourself with: %s",
                    curr_buff_len,
                    666,  # TODO: calculate bytes
                    "https://github.com/confluentinc/confluent-kafka-python/issues/137#issuecomment-282427382",
                )
            self._done()
            if self.output:
                self._kafka_simulator.render_records(self.output)

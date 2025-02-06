import signal
from inspect import GEN_SUSPENDED, getgeneratorstate
from time import sleep, time
from typing import Any, Literal, Optional

from confluent_kafka import KafkaException, TopicPartition
from confluent_kafka.error import KeySerializationError, ValueSerializationError
from confluent_kafka.serialization import MessageField, SerializationContext

from kafka_mocha.utils import validate_config
from kafka_mocha.buffer_handler import buffer_handler
from kafka_mocha.exceptions import KProducerMaxRetryException, KProducerTimeoutException
from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import PMessage
from kafka_mocha.signals import KSignals, Tick
from kafka_mocha.ticking_thread import TickingThread


class KProducer:
    def __init__(
        self,
        config: dict[str, Any],
        output: Optional[Literal["html", "csv"]] = None,
        loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "ERROR",
    ):
        validate_config("producer", config)
        self.config = config
        self.output = output
        self.logger = get_custom_logger(loglevel)
        self.buffer = []
        self._key_serializer = self.config.pop("key.serializer", None)
        self._value_serializer = self.config.pop("value.serializer", None)
        self._buffer_handler = buffer_handler(
            f"KProducer({id(self)})", self.buffer, self.config.pop("message.buffer", 300)
        )
        self._ticking_thread = TickingThread(f"KProducer({id(self)})", self._buffer_handler)
        self._max_retry_count = 3
        self._retry_backoff = 0.01
        self.transaction_inited = False
        self.transaction_begun = False

        self._buffer_handler.send(KSignals.INIT.value)
        self._kafka_simulator = KafkaSimulator()
        self._ticking_thread.start()

    def abort_transaction(self):
        self.purge()

    def begin_transaction(self):
        if not self.transaction_inited:
            raise KafkaException("TODO")
        if not self._ticking_thread.is_alive():
            self._ticking_thread = TickingThread(f"KProducer({id(self)})", self._buffer_handler)
        self.transaction_begun = True

    def commit_transaction(self):
        self._done()

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
        self.transaction_inited = True
        self.logger.warning("KProducer doesn't support transactions (yet). Skipping...")

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
        ctx = SerializationContext(topic, MessageField.KEY, headers)
        if self._key_serializer is not None:
            try:
                key = self._key_serializer(key, ctx)
            except Exception as se:
                raise KeySerializationError(se)
        ctx.field = MessageField.VALUE
        if self._value_serializer is not None:
            try:
                value = self._value_serializer(value, ctx)
            except Exception as se:
                raise ValueSerializationError(se)

        count = 0
        while count < self._max_retry_count:
            if getgeneratorstate(self._buffer_handler) == GEN_SUSPENDED:
                ack = self._buffer_handler.send(
                    PMessage.from_producer_data(
                        topic=topic,
                        partition=partition,
                        key=key,
                        value=value,
                        timestamp=timestamp,
                        headers=headers,
                        on_delivery=on_delivery,
                    )
                )
                self.logger.debug("KProducer(%d): received ack: %s", id(self), ack)
                break
            else:
                self.logger.debug("KProducer(%d): buffer is busy", id(self))
                count += 1
                sleep(count**2 * self._retry_backoff)
        else:
            raise KProducerMaxRetryException(f"Exceeded max send retries ({self._max_retry_count})")

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

    def _done(self):
        """Additional method to gracefully close message buffer."""
        self._ticking_thread.stop()
        self._ticking_thread.join()
        self._buffer_handler.close()

    def __del__(self):
        if hasattr(self, "config"):  # if __init__ was called without exceptions
            self._done()
            if self.output:
                self._kafka_simulator.render_records(self.output)

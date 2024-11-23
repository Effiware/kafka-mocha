from inspect import getgeneratorstate, GEN_SUSPENDED
from time import sleep
from typing import Any

from confluent_kafka import TopicPartition, KafkaException
from confluent_kafka.error import KeySerializationError, ValueSerializationError
from confluent_kafka.serialization import SerializationContext, MessageField

from kafka_mocha.buffer_handler import buffer_handler
from kafka_mocha.exceptions import KProducerMaxRetryException
from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import PMessage
from kafka_mocha.signals import KSignals, Tick
from kafka_mocha.ticking_thread import TickingThread

logger = get_custom_logger()


class KProducer:
    def __init__(self, config: dict[str, Any]):
        self.config = dict(config)
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

    def flush(self, timeout: float = None):
        """Duck type for confluent_kafka/cimpl.py::flush (see signature there).

        Sends `DONE` signal to message buffer handler in order to force sending buffered messages to Kafka Simulator.
        """
        count = 0
        while count < self._max_retry_count:
            if getgeneratorstate(self._buffer_handler) == GEN_SUSPENDED:
                self._buffer_handler.send(Tick.DONE)
                break
            else:
                count += 1
                sleep(count**2 * self._retry_backoff)
        else:
            raise KProducerMaxRetryException(f"Exceeded max send retries ({self._max_retry_count})")

    def init_transactions(self):
        self.transaction_inited = True
        logger.warning("KProducer doesn't support transactions (yet). Skipping...")

    def list_topics(self, topic: str = None, timeout: float = -1.0, *args, **kwargs):
        """Duck type for confluent_kafka/cimpl.py::list_topics (see signature there).

        Returns ClusterMetadata object from Kafka Simulator.
        """
        if timeout != -1.0:
            logger.warning("KProducer doesn't support timing out for this method. Parameter will be ignored.")

        return self._kafka_simulator.get_cluster_mdata(topic)

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
                logger.debug(f"KProducer({id(self)}): received ack: {ack}")
                break
            else:
                logger.debug(f"KProducer({id(self)}): buffer is busy")
                count += 1
                sleep(count**2 * self._retry_backoff)
        else:
            raise KProducerMaxRetryException(f"Exceeded max send retries ({self._max_retry_count})")

    def send_offsets_to_transaction(
        self, positions: list[TopicPartition], group_metadata: object, timeout: float = None
    ):
        raise NotImplementedError("Transactions are not yet fully supported in Kafka Mocha.")

    def set_sasl_credentials(self, *args, **kwargs):
        pass

    def _done(self):
        """Additional method to gracefully close message buffer."""
        self._ticking_thread.stop()
        self._ticking_thread.join()
        self._buffer_handler.close()


# producer = KProducer({})
# producer.produce("topic-1", "key".encode(), "value".encode(), on_delivery=lambda *_: None)
#
# producer._done()

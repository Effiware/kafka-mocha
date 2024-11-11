from inspect import getgeneratorstate, GEN_SUSPENDED
from time import sleep
from typing import Any

from confluent_kafka.error import KeySerializationError, ValueSerializationError
from confluent_kafka.serialization import SerializationContext, MessageField

from kafka_mocha.exceptions import KProducerMaxRetryException
from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.message_buffer import message_buffer
from kafka_mocha.models import PMessage
from kafka_mocha.signals import KSignals
from kafka_mocha.ticking_thread import TickingThread

logger = get_custom_logger()


class KProducer:
    def __init__(self, config: dict[str, Any]):
        self.config = dict(config)
        self._key_serializer = self.config.pop("key.serializer", None)
        self._value_serializer = self.config.pop("value.serializer", None)
        self._message_buffer = message_buffer(f"KProducer({id(self)})", self.config.pop("message.buffer", 300))
        self._ticking_thread = TickingThread(f"KProducer({id(self)})", self._message_buffer)
        self._max_retry_count = 3
        self._retry_backoff = 0.01

        self._message_buffer.send(KSignals.INIT.value)
        self._kafka_simulator = KafkaSimulator()
        self._ticking_thread.start()

    def list_topics(self, topic: str = None, timeout: float = -1.0, *args, **kwargs):
        if timeout != -1.0:
            logger.warning("KProducer doesn't support timing out for this method. Parameter will be ignored.")

        return self._kafka_simulator.get_topics(topic)

    def produce(self, topic, value=None, key=None, partition=-1, on_delivery=None, timestamp=0, headers=None) -> None:
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
            if getgeneratorstate(self._message_buffer) == GEN_SUSPENDED:
                ack = self._message_buffer.send(
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

    def _done(self):
        """Additional method to gracefully close message buffer."""
        self._ticking_thread.stop()
        self._ticking_thread.join()
        self._message_buffer.close()


# producer = KProducer({})
# producer.produce("topic-1", "key".encode(), "value".encode(), on_delivery=lambda *_: None)
#
# producer._done()

from inspect import getgeneratorstate, GEN_SUSPENDED
from time import sleep
from typing import Any

from confluent_kafka.error import KeySerializationError, ValueSerializationError
from confluent_kafka.serialization import SerializationContext, MessageField

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

        self._message_buffer.send(KSignals.INIT.value)
        self._ticking_thread.start()

    def produce(self, topic, key=None, value=None, partition=-1, on_delivery=None, timestamp=0, headers=None) -> None:
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

        MAX_COUNT = 3
        count = 0
        while count < MAX_COUNT:
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
                logger.info(f"KProducer({id(self)}): received ack: {ack}")
                break
            else:
                sleep(count ** 2 * 0.1)  # TODO: make it better
                logger.info(f"KProducer({id(self)}): buffer is busy")
                count += 1
        if 0 < count < MAX_COUNT:
            logger.warning(f"KProducer({id(self)}): succeeded in {count} try")
        elif count == MAX_COUNT:
            raise Exception("Exceeded max retries")

    def _done(self):
        self._ticking_thread.stop()
        self._ticking_thread.join()
        self._message_buffer.close()


# producer = KProducer({})
# producer.produce("topic-1", "key".encode(), "value".encode(), on_delivery=lambda *_: None)
#
# producer._done()

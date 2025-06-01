import doctest
import os

import confluent_kafka

from kafka_mocha import mock_consumer

TOPIC_NAME = "test-simple-consumer-topic"
LOCAL_INPUT = str(os.path.join(os.path.dirname(__file__), "inputs/users-registrations.json"))


@mock_consumer()
def invalid_configuration():
    """Mock consumer will always validate the configuration and raise exception in case of:
        - missing required configuration parameters
        - unknown configuration parameters
        - invalid configuration values/types

    >>> invalid_configuration()
    Traceback (most recent call last):
    ...
    kafka_mocha.exceptions.KafkaClientBootstrapException: Configuration validation errors: group.id is required for KConsumer
    """
    consumer = confluent_kafka.Consumer({"bootstrap.servers": "localhost:9092", "group.identifier": True, "foo": "bar"})
    consumer.list_topics(TOPIC_NAME)


@mock_consumer(inputs=[{"source": LOCAL_INPUT, "topic": TOPIC_NAME + "-poll"}], loglevel="INFO")
def consume_preloaded_messages():
    """Mock consumer will consume preloaded messages from the topic.

    >>> consume_preloaded_messages()
    Consumed message: {'key': '856254a0-7ec9-47cb-8f61-fd51e92eeb96', 'value': '{"user_id": "856254a0-7ec9-47cb-8f61-fd51e92eeb96", "user_name": "Albert", ...'}
    Consumed message: {'key': '237a917d-269f-4e20-96f3-0c4c43ac0d9c', 'value': '{"user_id": "237a917d-269f-4e20-96f3-0c4c43ac0d9c", "user_name": "Johnny", ...'}
    Consumed message: {'key': 'd1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6', 'value': '{"user_id": "d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6", "user_name": "Dakota", ...'}
    """
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group-poll",
            "auto.offset.reset": "earliest",
            "enable.auto.offset.store": False,
        }
    )
    consumer.subscribe([TOPIC_NAME + "-poll"])

    poll_num = 0
    try:
        while poll_num < 10:
            msg = consumer.poll(timeout=0.3)
            if msg is None:
                poll_num += 1
                continue
            if msg.error():
                raise confluent_kafka.KafkaException(msg.error())
            else:
                print(f"Consumed message: {{'key': '{msg.key()}', 'value': '{msg.value(None)[:75]}...'}}")
                consumer.store_offsets(msg)
                poll_num += 1
    finally:
        consumer.close()


@mock_consumer(inputs=[{"source": LOCAL_INPUT, "topic": TOPIC_NAME + "-batch", "serialize": False}])
def consume_preloaded_messages_batched():
    """Mock consumer will consume preloaded messages from the topic.

    >>> consume_preloaded_messages_batched()
    Consumed message: {'key': '856254a0-7ec9-47cb-8f61-fd51e92eeb96', 'value': '{"user_id": "856254a0-7ec9-47cb-8f61-fd51e92eeb96", "user_name": "Albert", ...'}
    Consumed message: {'key': '237a917d-269f-4e20-96f3-0c4c43ac0d9c', 'value': '{"user_id": "237a917d-269f-4e20-96f3-0c4c43ac0d9c", "user_name": "Johnny", ...'}
    Consumed message: {'key': 'd1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6', 'value': '{"user_id": "d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6", "user_name": "Dakota", ...'}
    """
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group-consume",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([TOPIC_NAME + "-batch"])
    msgs = consumer.consume(10, timeout=0.5)
    for msg in msgs:
        if msg.error():
            raise confluent_kafka.KafkaException(msg.error())
        else:
            print(f"Consumed message: {{'key': '{msg.key()}', 'value': '{msg.value(None)[:75]}...'}}")
    consumer.close()


if __name__ == "__main__":
    doctest.testmod(verbose=True)

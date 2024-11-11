from time import sleep

import pytest

from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.kproducer import KProducer


def test_kafka_simulator_received_messages__short_running_task():
    """Test that Kafka has written all sent messages for short-running task."""
    kafka = KafkaSimulator()
    producer = KProducer({})

    no_msg_to_produce = 10000
    for idx, _ in enumerate(range(no_msg_to_produce)):
        producer.produce("topic-1", "value".encode(), f"key-{idx}".encode(), on_delivery=lambda *_: None)

    producer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka is not None
    assert no_msg_appended == no_msg_to_produce


@pytest.mark.slow
def test_kafka_simulator_received_messages__medium_running_task():
    """Test that Kafka has written all sent messages for medium-running task."""
    kafka = KafkaSimulator()
    producer = KProducer({})

    no_msg_to_produce = 1000
    for idx, _ in enumerate(range(no_msg_to_produce)):
        sleep(0.01)
        producer.produce("topic-1", f"key-{idx}".encode(), "value".encode())

    producer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka is not None
    assert no_msg_appended == no_msg_to_produce


@pytest.mark.slow
def test_kafka_simulator_received_messages__long_running_task():
    """Test that Kafka has written all sent messages for running-running task."""
    kafka = KafkaSimulator()
    producer = KProducer({})

    no_msg_to_produce = 100
    for idx, _ in enumerate(range(no_msg_to_produce)):
        sleep(0.3)
        producer.produce("topic-1", f"key-{idx}".encode(), "value".encode(), on_delivery=lambda *_: None)

    producer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka is not None
    assert no_msg_appended == no_msg_to_produce
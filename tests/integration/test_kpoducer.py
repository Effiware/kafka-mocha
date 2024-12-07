from time import sleep

import pytest


def test_kafka_simulator_received_messages__short_running_task(kafka, kproducer):
    """Test that Kafka has written all sent messages for a short-running task."""

    no_msg_to_produce = 10000
    for idx, _ in enumerate(range(no_msg_to_produce)):
        kproducer.produce("topic-1", "value".encode(), f"key-{idx}".encode(), on_delivery=lambda *_: None)

    kproducer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka._instance is not None
    assert no_msg_appended == no_msg_to_produce


@pytest.mark.slow
def test_kafka_simulator_received_messages__medium_running_task(kafka, kproducer):
    """Test that Kafka has written all sent messages for a medium-running task."""

    no_msg_to_produce = 1000
    for idx, _ in enumerate(range(no_msg_to_produce)):
        sleep(0.01)
        kproducer.produce("topic-1", f"key-{idx}".encode(), "value".encode())

    kproducer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka._instance is not None
    assert no_msg_appended == no_msg_to_produce


@pytest.mark.slow
def test_kafka_simulator_received_messages__long_running_task(kafka, kproducer):
    """Test that Kafka has written all sent messages for a long-running task."""
    no_msg_to_produce = 100
    for idx, _ in enumerate(range(no_msg_to_produce)):
        sleep(0.3)
        kproducer.produce("topic-1", f"key-{idx}".encode(), "value".encode(), on_delivery=lambda *_: None)

    kproducer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka._instance is not None
    assert no_msg_appended == no_msg_to_produce

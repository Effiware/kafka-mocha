import doctest
from datetime import datetime

import confluent_kafka

from examples.confexmp import handle_produce
from kafka_mocha.wrappers import mock_producer

TOPIC_NAME = "test-topic"


@mock_producer()
def as_decorated_function():
    """It can be used as a direct function wrapper.

    >>> as_decorated_function()
    Mock message delivered (decorated function)
    """
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})

    # some pre-processing
    producer.produce(
        TOPIC_NAME,
        datetime.now().isoformat(),
        str(id(producer)),
        on_delivery=lambda err, msg: print("Mock message delivered (decorated function)"),
    )
    producer.flush()
    # some post-processing


def as_context_manager():
    """It can be used as a context manager.

    >>> as_context_manager()
    Mock message delivered (context manager)
    """
    with mock_producer():
        producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})

        # some pre-processing
        producer.produce(
            TOPIC_NAME,
            datetime.now().isoformat(),
            str(id(producer)),
            on_delivery=lambda err, msg: print("Mock message delivered (context manager)"),
        )
        producer.flush()
        # some post-processing


@mock_producer()
def as_class_instance():
    """It can be used as a class instance wrapper around a function.

    >>> as_class_instance()
    Message delivered
    Message delivered
    Message delivered
    """

    # some pre-processing
    handle_produce(TOPIC_NAME)
    # some post-processing


if __name__ == "__main__":
    doctest.testmod(verbose=True)

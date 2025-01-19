import doctest
from datetime import datetime

import confluent_kafka

from examples.confexmp import handle_produce
from kafka_mocha import mock_producer

TOPIC_NAME = "test-topic"


@mock_producer(loglevel="DEBUG")
def as_decorated_function():
    """It can be used as a direct function wrapper. Explicitly set loglevel to DEBUG.

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


@mock_producer(output="html")
def as_decorated_inner_function():
    """It can be used as a decorator around an inner function. Explicitly set output to HTML.

    >>> as_decorated_inner_function()
    Inner message delivered
    Inner message delivered
    Inner message delivered
    """

    # some pre-processing
    handle_produce(TOPIC_NAME)
    # some post-processing


if __name__ == "__main__":
    doctest.testmod(verbose=True)

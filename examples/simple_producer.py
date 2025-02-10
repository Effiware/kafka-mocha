import doctest
from datetime import datetime

import confluent_kafka

from examples.confexmp import handle_produce
from kafka_mocha import mock_producer

TOPIC_NAME = "test-topic"


@mock_producer()
def invalid_configuration():
    """Mock producer will always validate the configuration and raise exception in case of:
        - missing required configuration parameters
        - unknown configuration parameters
        - invalid configuration values/types

    >>> invalid_configuration()
    Traceback (most recent call last):
    ...
    kafka_mocha.exceptions.KafkaClientBootstrapException: Configuration validation errors: Value out of range for batch.size: expected (1, 2147483647), got False; Unknown configuration parameter: foo
    """
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092", "batch.size": False, "foo": "bar"})

    # some pre-processing
    producer.produce(
        TOPIC_NAME,
        datetime.now().isoformat(),
        str(id(producer)),
        on_delivery=lambda err, msg: print("Will not get here"),
    )
    producer.flush()
    # some post-processing


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


@mock_producer(output={"format": "html"})
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

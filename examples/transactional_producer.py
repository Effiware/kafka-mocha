import doctest
import os
from datetime import datetime

import confluent_kafka

TOPIC_NAME = "test-topic-transact"
os.environ["KAFKA_MOCHA_KSIM_TOPICS"] = f'["{TOPIC_NAME}-1:3", "{TOPIC_NAME}-2"]'

from kafka_mocha import mock_producer


@mock_producer()
def transactional_producer_basic():
    """Supports transactional producers. It can be used as a direct function wrapper.

    >>> transactional_producer_basic()
    Mock message delivered (inside kafka transaction)
    """
    producer = confluent_kafka.Producer(
        {"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "transactional.id": "test-id"}
    )
    producer.init_transactions()

    # some pre-processing
    producer.begin_transaction()
    producer.produce(
        TOPIC_NAME,
        datetime.now().isoformat(),
        str(id(producer)),
        on_delivery=lambda err, msg: print("Mock message delivered (inside kafka transaction)"),
    )
    producer.commit_transaction()
    # some post-processing


@mock_producer(output="csv")
def transactional_producer_multiple_topics():
    """Supports transactional producers. It can be used as a direct function wrapper. Explicitly set output to CSV.

    >>> transactional_producer_multiple_topics()
    Mock message delivered (inside kafka transaction) T.1.1
    Mock message delivered (inside kafka transaction) T.1.2
    Mock message delivered (inside kafka transaction) T.2.1
    """
    os.environ["KAFKA_MOCHA_KSIM_TOPICS"] = f'["{TOPIC_NAME}-1:3", "{TOPIC_NAME}-2"]'
    producer = confluent_kafka.Producer(
        {"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "transactional.id": "test-multiple"}
    )
    producer.init_transactions()

    # some pre-processing
    producer.begin_transaction()
    producer.produce(
        TOPIC_NAME + "-1",
        datetime.now().isoformat(),
        str(id(producer)),
        on_delivery=lambda err, msg: print("Mock message delivered (inside kafka transaction) T.1.1"),
    )
    producer.produce(
        TOPIC_NAME + "-1",
        datetime.now().isoformat(),
        str(id(producer) + 10),  # different key to change partition,
        on_delivery=lambda err, msg: print("Mock message delivered (inside kafka transaction) T.1.2"),
    )
    producer.produce(
        TOPIC_NAME + "-2",
        datetime.now().isoformat(),
        str(id(producer)),
        on_delivery=lambda err, msg: print("Mock message delivered (inside kafka transaction) T.2.1"),
    )
    producer.commit_transaction()
    # some post-processing


@mock_producer(output="csv")
def transactional_producer_unhappy_path():
    """It can be used as a direct function wrapper. Explicitly set loglevel to DEBUG.

    >>> transactional_producer_unhappy_path()
    """
    producer = confluent_kafka.Producer(
        {"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "transactional.id": "test-id"}
    )
    producer.init_transactions()

    # some pre-processing
    producer.begin_transaction()
    producer.produce(
        TOPIC_NAME,
        datetime.now().isoformat(),
        str(id(producer)),
        on_delivery=lambda err, msg: print("Any message shouldn't be visible here..."),
    )
    producer.abort_transaction()
    # some post-processing


if __name__ == "__main__":
    doctest.testmod(verbose=True)

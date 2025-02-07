import doctest
from datetime import datetime

import confluent_kafka

from kafka_mocha import mock_producer

TOPIC_NAME = "test-topic-transact"


@mock_producer(output="csv")
def transactional_producer_happy_path():
    """It can be used as a direct function wrapper. Explicitly set loglevel to DEBUG.

    >>> transactional_producer_happy_path()
    Mock message delivered (inside kafka transaction)
    """
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "transactional.id": "test-id"})
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
def transactional_producer_unhappy_path():
    """It can be used as a direct function wrapper. Explicitly set loglevel to DEBUG.

    >>> transactional_producer_unhappy_path()
    """
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "transactional.id": "test-id"})
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

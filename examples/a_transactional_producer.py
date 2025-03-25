import doctest
import os
from datetime import datetime
from threading import Thread
from time import sleep

import confluent_kafka

TOPIC_NAME = "test-transact-producer-topic"
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


@mock_producer(output={"format": "html", "name": "test-transaction-multi.html", "include_internal_topics": True})
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


@mock_producer(output={"format": "csv", "include_markers": True})
def transactional_producer_unhappy_path():
    """Aborted transactions are not visible in the output. Special markers are written into the topic.

    >>> transactional_producer_unhappy_path()
    """
    producer = confluent_kafka.Producer(
        {"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "transactional.id": "test-id-unhappy"}
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


def stale_transaction_fencing():
    """Stale transaction fencing. The first producer is fenced out by the second one.

    >>> stale_transaction_fencing() # doctest: +SKIP
    second_producer: transaction committed
    first_producer: KafkaError{FATAL,code=_FENCED,val=-144,str="Failed to end transaction: Local: This instance has been fenced by a newer instance"}
    """

    class ProducerThread(Thread):
        def __init__(self, name: str, run_id: int):
            Thread.__init__(self, name=name)
            self.run_id = run_id

        def run(self) -> None:
            with mock_producer():
                producer = confluent_kafka.Producer(
                    {"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "transactional.id": "same-id"}
                )
                producer.init_transactions()
                producer.begin_transaction()
                producer.produce(TOPIC_NAME, datetime.now().isoformat(), str(self.run_id))

                sleep(3) if self.run_id % 2 == 0 else sleep(1)  # simulate a delay/crash for the first producer
                try:
                    producer.commit_transaction()
                except confluent_kafka.KafkaException as e:
                    print(f"{self.name}: {e}")
                else:
                    print(f"{self.name}: transaction committed")


    producing_thread_0 = ProducerThread(name="first_producer", run_id=0)
    producing_thread_1 = ProducerThread(name="second_producer", run_id=1)

    producing_thread_0.start()
    producing_thread_1.start()

    producing_thread_1.join()  # the second producer should fence out the first one
    producing_thread_0.join()  # the first producer should raise an exception


if __name__ == "__main__":
    doctest.testmod(verbose=True)

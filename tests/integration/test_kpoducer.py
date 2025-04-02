from random import randint
from time import sleep

import pytest
from confluent_kafka import KafkaError, KafkaException

from kafka_mocha.kproducer import KProducer


def test_kproducer_returns_produced_messages_no__unhappy(kproducer) -> None:
    """Test that Kafka producer returns number of produced messages - when nothing produced."""
    assert kproducer.m__get_all_produced_messages_no("test-number-topic") == 0


def test_kproducer_returns_produced_messages_no__happy(kproducer) -> None:
    """Test that Kafka producer returns number of produced messages."""
    kproducer.produce("test-number-topic", b"key-1", b"value-1")
    kproducer.produce("test-number-topic", b"key-2", b"value-2")
    kproducer.flush()
    assert kproducer.m__get_all_produced_messages_no("test-number-topic") == 2


def test_kafka_simulator_received_messages__short_running_task(kafka, kproducer):
    """Test that Kafka has written all sent messages for a short-running task."""

    no_msg_to_produce = 10000
    for idx, _ in enumerate(range(no_msg_to_produce)):
        kproducer.produce("topic-1", "value".encode(), f"key-{idx}".encode(), on_delivery=lambda *_: randint(1, 100))

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
        kproducer.produce("topic-1", value=f"value-{idx}".encode())

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
        kproducer.produce(
            "topic-1",
            f"key-{idx}".encode(),
            "value".encode(),
            headers=[(f"hkey-{idx}", b"hvalue")],
            on_delivery=lambda err, msg: print(f"Error: {err}") if err else print(f"Message delivered: {msg.offset()}")
        )

    kproducer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka._instance is not None
    assert no_msg_appended == no_msg_to_produce


class TestTransactionFlow:

    @pytest.fixture(scope="class")
    def own_producer(
        self,
    ) -> KProducer:
        producer = KProducer(
            {
                "bootstrap.servers": "localhost:9092",
                "enable.idempotence": True,
                "transactional.id": "test-transaction-flow",
            }
        )
        return producer

    @pytest.mark.parametrize("action", ["begin", "commit", "abort"])
    def test_that_transaction_initialization_is_needed(self, own_producer: KProducer, action: str) -> None:
        """Test that transaction coordinator fences out old transactions."""
        match action:
            case "begin":
                with pytest.raises(KafkaException) as exc:
                    own_producer.begin_transaction()
                assert exc.value.args[0].code() == KafkaError._STATE
                assert exc.value.args[0].str() == "Operation not valid in state Init"
                assert exc.value.args[0].fatal()
            case "commit":
                with pytest.raises(KafkaException) as exc:
                    own_producer.commit_transaction()
                assert exc.value.args[0].code() == KafkaError._STATE
                assert exc.value.args[0].str() == "Operation not valid in state Init"
                assert exc.value.args[0].fatal()
            case "abort":
                with pytest.raises(KafkaException) as exc:
                    own_producer.abort_transaction()
                assert exc.value.args[0].code() == KafkaError._STATE
                assert exc.value.args[0].str() == "Operation not valid in state Init"
                assert exc.value.args[0].fatal()

    # def test_that_transaction_coordinator_can_begin_transaction(
    #     self, kafka, transaction_id: str, new_producer_id: int, transaction_end: str
    # ) -> None:
    #     """Test that transaction coordinator can begin transaction."""
    #     kafka.transaction_coordinator("begin", new_producer_id, transaction_id)
    #
    # def test_that_transaction_coordinator_can_commit_transaction(
    #     self, kafka, transaction_id: str, new_producer_id: int, transaction_end: str
    # ) -> None:
    #     """Test that transaction coordinator can commit transaction."""
    #     kafka.transaction_coordinator(transaction_end, new_producer_id, transaction_id)  # noqa

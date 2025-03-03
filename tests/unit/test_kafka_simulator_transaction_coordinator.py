import pytest
from confluent_kafka import KafkaError, KafkaException

from kafka_mocha.kafka_simulator import KafkaSimulator


@pytest.mark.parametrize("transaction_state", ["begin", "commit", "abort"])
def test_that_init_transaction_is_needed(fresh_kafka, transaction_state) -> None:
    """Test that transaction coordinator raises an exception when transaction is not initialized."""
    with pytest.raises(KafkaException) as exc:
        fresh_kafka.transaction_coordinator(transaction_state, 1, "test-transaction")

    assert isinstance(exc.value.args[0], KafkaError)
    assert exc.value.args[0].code() == KafkaError._STATE
    assert exc.value.args[0].str() == "Operation not valid in state Init"
    assert exc.value.args[0].fatal()


@pytest.mark.parametrize("transaction_end", ["commit", "abort"])
class TestTransactionCoordinator:
    """Test KafkaSimulator transaction coordinator. Tests here are stateful and should be run in order."""

    @pytest.fixture(scope="class")
    def transaction_id(self) -> str:
        return "test-transaction"

    @pytest.fixture(scope="class")
    def old_producer_id(self) -> int:
        return 6

    @pytest.fixture(scope="class")
    def new_producer_id(self) -> int:
        return 7

    @pytest.fixture(scope="class")
    def kafka(self, transaction_id: str, old_producer_id: int) -> KafkaSimulator:
        kafka = KafkaSimulator()
        kafka.transaction_coordinator("init", old_producer_id, transaction_id)
        return kafka

    def test_that_transaction_coordinator_fences_out_old_transactions(
        self, kafka, transaction_id: str, old_producer_id: int, new_producer_id: int, transaction_end: str
    ) -> None:
        """Test that transaction coordinator fences out old transactions."""
        assert old_producer_id in kafka._registered_transact_ids[transaction_id]
        # assert kafka._registered_transact_ids[transaction_id][-1] == old_producer_id

        kafka.transaction_coordinator("init", new_producer_id, transaction_id)
        assert old_producer_id in kafka._registered_transact_ids[transaction_id]
        assert new_producer_id in kafka._registered_transact_ids[transaction_id]
        assert kafka._registered_transact_ids[transaction_id][-1] == new_producer_id

    def test_that_transaction_coordinator_can_begin_transaction(
        self, kafka, transaction_id: str, new_producer_id: int, transaction_end: str
    ) -> None:
        """Test that transaction coordinator can begin transaction."""
        kafka.transaction_coordinator("begin", new_producer_id, transaction_id)

    def test_that_transaction_coordinator_can_commit_transaction(
        self, kafka, transaction_id: str, new_producer_id: int, transaction_end: str
    ) -> None:
        """Test that transaction coordinator can commit transaction."""
        kafka.transaction_coordinator(transaction_end, new_producer_id, transaction_id)  # noqa

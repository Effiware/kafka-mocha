import pytest
from confluent_kafka import KafkaError, KafkaException


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
def test_that_transaction_coordinator_fences_out_old_transactions(fresh_kafka, transaction_end: str) -> None:
    """Test that transaction coordinator fences out old transactions."""
    transaction_id = "fencing-out-transaction"
    old_producer_id = 6
    new_producer_id = 7

    fresh_kafka.transaction_coordinator("init", old_producer_id, transaction_id)
    assert old_producer_id in map(lambda x: x[0], fresh_kafka._registered_transact_ids[transaction_id])
    assert fresh_kafka._registered_transact_ids[transaction_id][-1][0] == old_producer_id

    fresh_kafka.transaction_coordinator("init", new_producer_id, transaction_id)
    assert old_producer_id in map(lambda x: x[0], fresh_kafka._registered_transact_ids[transaction_id])
    assert new_producer_id in map(lambda x: x[0], fresh_kafka._registered_transact_ids[transaction_id])
    assert fresh_kafka._registered_transact_ids[transaction_id][-1][0] == new_producer_id

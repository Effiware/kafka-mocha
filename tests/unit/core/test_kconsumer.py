from inspect import GEN_SUSPENDED, getgeneratorstate
from unittest.mock import MagicMock, patch

import confluent_kafka
import pytest

from kafka_mocha.core.kafka_simulator import KafkaSimulator
from kafka_mocha.core.kconsumer import KConsumer
from kafka_mocha.exceptions import KafkaClientBootstrapException, KConsumerMaxRetryException
from kafka_mocha.models.kmodels import KMessage


def test_kconsumer_initialization(kconsumer) -> None:
    """Test that KConsumer initializes properly."""
    assert kconsumer is not None
    assert kconsumer._group_id == "test-group"
    assert kconsumer._subscription == []
    assert kconsumer._assignment == []
    assert kconsumer._positions == {}
    assert getgeneratorstate(kconsumer._kafka_simulator.consumers_handler) == GEN_SUSPENDED


def test_kconsumer_requires_group_id() -> None:
    """Test that KConsumer requires a group.id."""
    with pytest.raises(KafkaClientBootstrapException) as exc:
        KConsumer({"bootstrap.servers": "localhost:9092"})

    assert "group.id is required" in str(exc.value)


def test_kconsumer_validates_auto_offset_reset(kafka) -> None:
    """Test that KConsumer validates auto.offset.reset values."""
    # Valid values should work
    consumer = KConsumer(
        {"bootstrap.servers": "localhost:9092", "group.id": "test-group", "auto.offset.reset": "earliest"}
    )
    assert consumer._auto_offset_reset == "earliest"

    consumer = KConsumer(
        {"bootstrap.servers": "localhost:9092", "group.id": "test-group", "auto.offset.reset": "latest"}
    )
    assert consumer._auto_offset_reset == "latest"

    consumer = KConsumer(
        {"bootstrap.servers": "localhost:9092", "group.id": "test-group", "auto.offset.reset": "error"}
    )
    assert consumer._auto_offset_reset == "error"

    # Invalid value should raise exception
    with pytest.raises(Exception) as exc:
        KConsumer({"bootstrap.servers": "localhost:9092", "group.id": "test-group", "auto.offset.reset": "invalid"})

    # Just check that an exception was raised with the right message
    assert "auto.offset.reset" in str(exc.value)


# Subscription and Assignment Tests


def test_kconsumer_subscribe(kconsumer, monkeypatch) -> None:
    """Test subscription to topics."""

    # Mock get_member_assignment to return a test assignment
    def mock_get_member_assignment(self, consumer_id):
        return [confluent_kafka.TopicPartition("test-topic", 0)]

    monkeypatch.setattr(KafkaSimulator, "get_member_assignment", mock_get_member_assignment)

    kconsumer.subscribe(["test-topic"])
    assert kconsumer._subscription == ["test-topic"]
    assert len(kconsumer._assignment) == 1

    # Check that assigned partition is for the subscribed topic
    assert kconsumer._assignment[0].topic == "test-topic"
    assert kconsumer._assignment[0].partition == 0


def test_kconsumer_unsubscribe(kconsumer_with_subscription) -> None:
    """Test unsubscribing from topics."""
    assert kconsumer_with_subscription._subscription == ["test-topic"]

    kconsumer_with_subscription.unsubscribe()
    assert kconsumer_with_subscription._subscription == []
    assert kconsumer_with_subscription._assignment == []
    assert kconsumer_with_subscription._positions == {}


def test_kconsumer_assign(kconsumer) -> None:
    """Test manual partition assignment."""
    partitions = [confluent_kafka.TopicPartition("test-topic", 0), confluent_kafka.TopicPartition("test-topic", 1)]

    kconsumer.assign(partitions)
    assert len(kconsumer._assignment) == 2

    # Check that assignment contains the partitions we specified
    topics_and_partitions = [(tp.topic, tp.partition) for tp in kconsumer._assignment]
    assert ("test-topic", 0) in topics_and_partitions
    assert ("test-topic", 1) in topics_and_partitions

    # Check that positions are initialized
    assert "test-topic" in kconsumer._positions
    assert 0 in kconsumer._positions["test-topic"]
    assert 1 in kconsumer._positions["test-topic"]


def test_kconsumer_unassign(kconsumer_with_assignment) -> None:
    """Test removing assignment."""
    assert len(kconsumer_with_assignment._assignment) > 0

    kconsumer_with_assignment.unassign()
    assert kconsumer_with_assignment._assignment == []
    assert kconsumer_with_assignment._positions == {}


def test_kconsumer_incremental_assign(kconsumer_with_assignment) -> None:
    """Test incremental assignment."""
    initial_assignment_len = len(kconsumer_with_assignment._assignment)

    # Add a new partition incrementally
    kconsumer_with_assignment.incremental_assign([confluent_kafka.TopicPartition("test-topic", 1)])

    # Check that assignment grew by 1
    assert len(kconsumer_with_assignment._assignment) == initial_assignment_len + 1

    # Check that the new partition is in the assignment
    topics_and_partitions = [(tp.topic, tp.partition) for tp in kconsumer_with_assignment._assignment]
    assert ("test-topic", 1) in topics_and_partitions

    # Check that position for the new partition is initialized
    assert 1 in kconsumer_with_assignment._positions["test-topic"]


def test_kconsumer_incremental_unassign(kconsumer_with_assignment) -> None:
    """Test incremental unassignment."""
    # First add another partition
    kconsumer_with_assignment.incremental_assign([confluent_kafka.TopicPartition("test-topic", 1)])
    assert len(kconsumer_with_assignment._assignment) == 2

    # Then remove one partition incrementally
    partition_to_remove = next(tp for tp in kconsumer_with_assignment._assignment if tp.partition == 0)
    kconsumer_with_assignment.incremental_unassign([partition_to_remove])

    # Check that assignment shrunk by 1
    assert len(kconsumer_with_assignment._assignment) == 1

    # Check that the removed partition is no longer in the assignment
    topics_and_partitions = [(tp.topic, tp.partition) for tp in kconsumer_with_assignment._assignment]
    assert ("test-topic", 0) not in topics_and_partitions
    assert ("test-topic", 1) in topics_and_partitions

    # Check that position for the removed partition is removed
    assert 0 not in kconsumer_with_assignment._positions["test-topic"]
    assert 1 in kconsumer_with_assignment._positions["test-topic"]


# Offset Management Tests


def test_kconsumer_commit(kconsumer_with_assignment) -> None:
    """Test committing offsets."""
    # Test committing current positions
    kconsumer_with_assignment._positions["test-topic"][0] = 100
    commit_result = kconsumer_with_assignment.commit()
    assert commit_result is None  # async commit returns None

    # Test committing with a message
    test_message = KMessage("test-topic", 0, b"key", b"value")
    test_message.set_offset(200)
    commit_result = kconsumer_with_assignment.commit(message=test_message)
    assert commit_result is None

    # Test committing with specific offsets
    offsets_to_commit = [confluent_kafka.TopicPartition("test-topic", 0, 300)]
    commit_result = kconsumer_with_assignment.commit(offsets=offsets_to_commit)
    assert commit_result is None

    # Test synchronous commit
    offsets_to_commit = [confluent_kafka.TopicPartition("test-topic", 0, 400)]
    commit_result = kconsumer_with_assignment.commit(offsets=offsets_to_commit, asynchronous=False)
    assert commit_result is not None
    assert len(commit_result) == 1
    assert commit_result[0].topic == "test-topic"
    assert commit_result[0].partition == 0
    assert commit_result[0].offset == 400


def test_kconsumer_store_offsets(kafka) -> None:
    """Test storing offsets."""
    # Create a consumer with default settings (auto.offset.store=True)
    consumer = KConsumer({"bootstrap.servers": "localhost:9092", "group.id": "test-group"})
    consumer.assign([confluent_kafka.TopicPartition("test-topic", 0)])

    # Enable auto.offset.store should cause store_offsets to fail
    with pytest.raises(confluent_kafka.KafkaException) as exc:
        consumer.store_offsets()

    # Check that an exception was raised with the expected message
    assert "store_offsets() requires 'enable.auto.offset.store=False'" in str(exc.value)

    # Create a consumer with auto.offset.store=False
    with patch.object(KMessage, "value", lambda self, payload: b"value"):
        consumer2 = KConsumer(
            {"bootstrap.servers": "localhost:9092", "group.id": "test-group", "enable.auto.offset.store": False}
        )
        consumer2.assign([confluent_kafka.TopicPartition("test-topic", 0)])

        # Test storing with a message
        test_message = KMessage("test-topic", 0, b"key", b"value")
        test_message.set_offset(200)

        consumer2.store_offsets(message=test_message)
        assert consumer2._positions["test-topic"][0] == 201  # offset + 1

        # Test storing with specific offsets
        offsets_to_store = [confluent_kafka.TopicPartition("test-topic", 0, 300)]
        consumer2.store_offsets(offsets=offsets_to_store)
        assert consumer2._positions["test-topic"][0] == 300


def test_kconsumer_position(kconsumer_with_assignment) -> None:
    """Test getting current position."""
    # Set a position
    kconsumer_with_assignment._positions["test-topic"][0] = 100

    # Get positions
    positions = kconsumer_with_assignment.position([confluent_kafka.TopicPartition("test-topic", 0)])

    assert len(positions) == 1
    assert positions[0].topic == "test-topic"
    assert positions[0].partition == 0
    assert positions[0].offset == 100


def test_kconsumer_committed(kconsumer_with_assignment, monkeypatch) -> None:
    """Test getting committed offsets."""

    # Mock get_committed_offsets to return test offsets
    def mock_get_committed_offsets(self, consumer_id, partitions):
        return [confluent_kafka.TopicPartition(tp.topic, tp.partition, 100) for tp in partitions]

    monkeypatch.setattr(KafkaSimulator, "get_committed_offsets", mock_get_committed_offsets)

    # Get committed offsets
    committed_offsets = kconsumer_with_assignment.committed([confluent_kafka.TopicPartition("test-topic", 0)])

    assert len(committed_offsets) == 1
    assert committed_offsets[0].topic == "test-topic"
    assert committed_offsets[0].partition == 0
    assert committed_offsets[0].offset == 100


def test_kconsumer_poll_with_no_messages(kconsumer_with_assignment, monkeypatch) -> None:
    """Test polling with no messages."""
    # Instead of trying to mock the generator methods directly, let's mock the handle_consumers
    # method of the KafkaSimulator to return a new generator

    def mock_handle_consumers():
        while True:
            request = yield []

    # Create a new generator from our mock
    mock_generator = mock_handle_consumers()
    next(mock_generator)  # Prime the generator

    # Patch the consumers_handler with our mock
    monkeypatch.setattr(kconsumer_with_assignment._kafka_simulator, "consumers_handler", mock_generator)

    # Poll should return None when no messages are available and timeout is 0
    result = kconsumer_with_assignment.poll(0)
    assert result is None


def test_kconsumer_poll_with_messages(kconsumer_with_assignment, monkeypatch) -> None:
    """Test polling with messages."""
    # Create a test message to return
    test_message = KMessage("test-topic", 0, b"key", b"value")
    test_message.set_offset(100)

    # Mock the handle_consumers generator to return our test message
    def mock_handle_consumers():
        while True:
            request = yield [test_message]

    # Create a new generator from our mock
    mock_generator = mock_handle_consumers()
    next(mock_generator)  # Prime the generator

    # Patch the consumers_handler with our mock
    monkeypatch.setattr(kconsumer_with_assignment._kafka_simulator, "consumers_handler", mock_generator)

    # Mock the value method since it has an unexpected parameter
    with patch.object(KMessage, "value", return_value=b"value"):
        # Poll should return the message
        result = kconsumer_with_assignment.poll(0)
        assert result is not None
        assert result.topic() == "test-topic"
        assert result.partition() == 0
        assert result.offset() == 100
        assert result.key() == b"key"
        assert result.value() == b"value"

        # Check that position was updated
        assert kconsumer_with_assignment._positions["test-topic"][0] == 101


def test_kconsumer_consume_with_no_messages(kconsumer_with_assignment, monkeypatch) -> None:
    """Test consume with no messages."""
    # Instead of trying to mock the generator methods directly, let's mock the handle_consumers
    # method of the KafkaSimulator to return a new generator

    def mock_handle_consumers():
        while True:
            request = yield []

    # Create a new generator from our mock
    mock_generator = mock_handle_consumers()
    next(mock_generator)  # Prime the generator

    # Patch the consumers_handler with our mock
    monkeypatch.setattr(kconsumer_with_assignment._kafka_simulator, "consumers_handler", mock_generator)

    # Consume should return an empty list when no messages are available and timeout is 0
    result = kconsumer_with_assignment.consume(10, 0)
    assert result == []


def test_kconsumer_consume_with_messages(kconsumer_with_assignment, monkeypatch) -> None:
    """Test consume with messages."""
    # Create test messages to return
    messages = [
        KMessage("test-topic", 0, b"key1", b"value1"),
        KMessage("test-topic", 0, b"key2", b"value2"),
        KMessage("test-topic", 0, b"key3", b"value3"),
    ]
    for i, msg in enumerate(messages):
        msg.set_offset(100 + i)

    # Mock the handle_consumers generator to return our test messages
    def mock_handle_consumers():
        while True:
            request = yield messages

    # Create a new generator from our mock
    mock_generator = mock_handle_consumers()
    next(mock_generator)  # Prime the generator

    # Patch the consumers_handler with our mock
    monkeypatch.setattr(kconsumer_with_assignment._kafka_simulator, "consumers_handler", mock_generator)

    # Create individual return values for each message's value() method
    value_mocks = {
        100: MagicMock(return_value=b"value1"),
        101: MagicMock(return_value=b"value2"),
        102: MagicMock(return_value=b"value3"),
    }

    # Patch KMessage.value with a lambda that chooses the right mock based on offset
    with patch.object(KMessage, "value", lambda self, payload: value_mocks[self.offset()](payload)):
        # Consume should return the messages
        result = kconsumer_with_assignment.consume(10, 0)
        assert len(result) == 3

        # Verify the messages
        for i, msg in enumerate(result):
            assert msg.topic() == "test-topic"
            assert msg.partition() == 0
            assert msg.offset() == 100 + i
            assert msg.key() == f"key{i+1}".encode()
            assert msg.value(None) == f"value{i+1}".encode()  # Pass None as payload

        # Check that position was updated to the latest offset + 1
        assert kconsumer_with_assignment._positions["test-topic"][0] == 103


# Consumer Group Tests


def test_kconsumer_memberid(kconsumer) -> None:
    """Test getting member ID."""
    assert kconsumer.memberid() is not None
    assert isinstance(kconsumer.memberid(), str)
    assert kconsumer.memberid().startswith("mock-consumer-")


def test_kconsumer_consumer_group_metadata(kconsumer) -> None:
    """Test getting consumer group metadata."""
    metadata = kconsumer.consumer_group_metadata()
    assert metadata is not None
    assert hasattr(metadata, "group_id")
    assert hasattr(metadata, "member_id")
    assert metadata.group_id == "test-group"
    assert metadata.member_id == kconsumer.memberid()


# Callback Tests


def test_kconsumer_on_assign_callback(monkeypatch) -> None:
    """Test on_assign callback."""
    # Create a mock callback
    on_assign_mock = MagicMock()

    # Mock get_member_assignment to return test assignments
    def mock_get_member_assignment(self, consumer_id):
        return [confluent_kafka.TopicPartition("test-topic", 0)]

    monkeypatch.setattr(KafkaSimulator, "get_member_assignment", mock_get_member_assignment)

    # Create a consumer with the callback
    with patch("kafka_mocha.utils._validate_against_schema"):
        consumer = KConsumer({"bootstrap.servers": "localhost:9092", "group.id": "test-group"})

        # Subscribe with the callback
        consumer.subscribe(["test-topic"], on_assign=on_assign_mock)

        # Check that the callback was called
        on_assign_mock.assert_called_once()

        # Check that the callback was called with the consumer and a list of partitions
        args = on_assign_mock.call_args[0]
        assert args[0] == consumer
        assert isinstance(args[1], list)
        assert all(isinstance(tp, confluent_kafka.TopicPartition) for tp in args[1])


def test_kconsumer_on_revoke_callback(monkeypatch) -> None:
    """Test on_revoke callback."""
    # Create a mock callback
    on_revoke_mock = MagicMock()

    # Create a consumer with the callback and mock assignment
    with patch("kafka_mocha.utils._validate_against_schema"):
        consumer = KConsumer({"bootstrap.servers": "localhost:9092", "group.id": "test-group"})

        # Manually set up assignment
        consumer._assignment = [confluent_kafka.TopicPartition("test-topic", 0)]

        # Subscribe with the callback
        consumer.subscribe(["test-topic"], on_revoke=on_revoke_mock)

        # Directly call the revoke callback method
        consumer._on_partition_revoke(consumer._assignment)

        # Check that the callback was called
        on_revoke_mock.assert_called_once()

        # Check that the callback was called with the consumer and a list of partitions
        args = on_revoke_mock.call_args[0]
        assert args[0] == consumer
        assert isinstance(args[1], list)


# Abstraction Layer Tests


def test_kconsumer_fetch_with_retry_success(kconsumer_with_assignment, monkeypatch) -> None:
    """Test _fetch_with_retry method succeeds on first try."""

    # Mock successful generator interaction
    def mock_handle_consumers():
        while True:
            request = yield [KMessage("test-topic", 0, b"key", b"value")]

    mock_generator = mock_handle_consumers()
    next(mock_generator)  # Prime the generator

    monkeypatch.setattr(kconsumer_with_assignment._kafka_simulator, "consumers_handler", mock_generator)

    # Test the method
    request = (id(kconsumer_with_assignment), [confluent_kafka.TopicPartition("test-topic", 0, 0)], 1)
    messages = kconsumer_with_assignment._fetch_with_retry(request)

    assert len(messages) == 1
    assert messages[0].topic() == "test-topic"


def test_kconsumer_fetch_with_retry_max_retries(kconsumer_with_assignment, monkeypatch) -> None:
    """Test _fetch_with_retry raises exception when max retries exceeded."""

    def mock_getgeneratorstate(generator):
        """Mock getgeneratorstate to always return a non-suspended state"""
        return "GEN_RUNNING"  # Not suspended

    monkeypatch.setattr("kafka_mocha.core.kconsumer.getgeneratorstate", mock_getgeneratorstate)

    # Set low retry count and backoff for fast testing
    kconsumer_with_assignment._max_retry_count = 2
    kconsumer_with_assignment._retry_backoff = 0.001

    request = (id(kconsumer_with_assignment), [confluent_kafka.TopicPartition("test-topic", 0, 0)], 1)

    with pytest.raises(KConsumerMaxRetryException) as exc_info:
        kconsumer_with_assignment._fetch_with_retry(request)

    assert "Exceeded max consume retries (2)" in str(exc_info.value)


def test_kconsumer_consume_messages_abstraction(kconsumer_with_assignment, monkeypatch) -> None:
    """Test _consume_messages abstraction method."""
    test_messages = [KMessage("test-topic", 0, b"key1", b"value1"), KMessage("test-topic", 0, b"key2", b"value2")]
    test_messages[0].set_offset(100)
    test_messages[1].set_offset(101)

    # Mock _fetch_with_retry to return test messages
    def mock_fetch_with_retry(self, request, timeout=None):
        return test_messages

    monkeypatch.setattr(KConsumer, "_fetch_with_retry", mock_fetch_with_retry)

    # Mock _update_positions_and_commit to track calls
    update_calls = []

    def mock_update_positions_and_commit(self, messages):
        update_calls.append(messages)

    monkeypatch.setattr(KConsumer, "_update_positions_and_commit", mock_update_positions_and_commit)

    # Test the method
    result = kconsumer_with_assignment._consume_messages(5)

    assert result == test_messages
    assert len(update_calls) == 1
    assert update_calls[0] == test_messages


def test_kconsumer_update_positions_and_commit(kconsumer_with_assignment) -> None:
    """Test _update_positions_and_commit method."""
    # Create test messages
    messages = [
        KMessage("test-topic", 0, b"key1", b"value1"),
        KMessage("test-topic", 0, b"key2", b"value2"),
        KMessage("other-topic", 1, b"key3", b"value3"),
    ]
    messages[0].set_offset(10)
    messages[1].set_offset(11)
    messages[2].set_offset(20)

    # Initialize positions
    kconsumer_with_assignment._positions = {}

    # Test the method
    kconsumer_with_assignment._update_positions_and_commit(messages)

    # Verify positions were updated correctly
    assert kconsumer_with_assignment._positions["test-topic"][0] == 12  # Last offset + 1
    assert kconsumer_with_assignment._positions["other-topic"][1] == 21  # Last offset + 1


# def test_kconsumer_maybe_auto_commit(kconsumer_with_assignment, monkeypatch) -> None:
#     """Test _maybe_auto_commit method."""
#     # Set up positions
#     kconsumer_with_assignment._positions = {"test-topic": {0: 100}, "other-topic": {1: 200}}
#
#     # Mock the kafka simulator's commit_offsets method
#     commit_calls = []
#
#     def mock_commit_offsets(consumer_id, offsets):
#         commit_calls.append((consumer_id, offsets))
#
#     # Test the method
#     kconsumer_with_assignment._maybe_auto_commit()
#
#     # Verify commit was called with correct offsets
#     assert len(commit_calls) == 1
#     consumer_id, offsets = commit_calls[0]
#     assert consumer_id == id(kconsumer_with_assignment)
#     assert len(offsets) == 2
#
#     # Check that offsets contain our positions
#     offset_tuples = [(tp.topic, tp.partition, tp.offset) for tp in offsets]
#     assert ("test-topic", 0, 100) in offset_tuples
#     assert ("other-topic", 1, 200) in offset_tuples


def test_kconsumer_consume_uses_abstraction(kconsumer_with_assignment, monkeypatch) -> None:
    """Test that consume() method uses _consume_messages abstraction."""
    test_messages = [KMessage("test-topic", 0, b"key", b"value")]

    # Mock _consume_messages to track calls
    consume_calls = []

    def mock_consume_messages(self, num_messages):
        consume_calls.append(num_messages)
        return test_messages

    monkeypatch.setattr(KConsumer, "_consume_messages", mock_consume_messages)

    # Test consume method
    result = kconsumer_with_assignment.consume(5, timeout=0)

    # Verify abstraction was called correctly
    assert len(consume_calls) == 1
    assert consume_calls[0] == 5
    assert result == test_messages


def test_kconsumer_poll_uses_abstraction(kconsumer_with_assignment, monkeypatch) -> None:
    """Test that poll() method uses _consume_messages abstraction."""
    test_message = KMessage("test-topic", 0, b"key", b"value")

    # Mock _consume_messages to return one message
    def mock_consume_messages(self, num_messages):
        assert num_messages == 1  # poll should request exactly 1 message
        return [test_message]

    monkeypatch.setattr(KConsumer, "_consume_messages", mock_consume_messages)

    # Test poll method
    result = kconsumer_with_assignment.poll(timeout=0)

    # Verify result
    assert result == test_message


def test_kconsumer_poll_no_messages_uses_abstraction(kconsumer_with_assignment, monkeypatch) -> None:
    """Test that poll() returns None when no messages available."""

    # Mock _consume_messages to return empty list
    def mock_consume_messages(self, num_messages):
        return []

    monkeypatch.setattr(KConsumer, "_consume_messages", mock_consume_messages)

    # Test poll method
    result = kconsumer_with_assignment.poll(timeout=0)

    # Verify result is None
    assert result is None


# Error Handling Tests


def test_kconsumer_retry_mechanism_configuration(kafka) -> None:
    """Test that retry mechanism can be configured via consumer config."""
    consumer = KConsumer(
        {"bootstrap.servers": "localhost:9092", "group.id": "test-group", "retries": 10, "retry.backoff.ms": 50}
    )

    assert consumer._max_retry_count == 10
    assert consumer._retry_backoff == 0.05  # Converted to seconds

    consumer.close()


def test_kconsumer_exception_import() -> None:
    """Test that KConsumerMaxRetryException is properly imported."""
    from kafka_mocha.exceptions import KConsumerMaxRetryException

    # Should be able to create an instance
    exception = KConsumerMaxRetryException("Test message")
    assert str(exception) == "Test message"

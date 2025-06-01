import pytest

from kafka_mocha.core.buffer_handler import get_partitioner

topics = {"topic-1": {"partition_no": 3}, "topic-2": {"partition_no": 2}}


def test_default_partitioner() -> None:
    """Test that default partitioner works as intended."""
    partitioner = get_partitioner(topics)

    assert 0 <= partitioner("topic-1", b"key-1") <= 2
    assert 0 <= partitioner("topic-1", b"key-2") <= 2
    assert 0 <= partitioner("topic-2", b"key-3") <= 2

    assert 0 <= partitioner("topic-2", b"key-1") <= 1
    assert 0 <= partitioner("topic-2", b"key-2") <= 1

    assert partitioner("topic-3", b"key-1") == 0
    assert partitioner("topic-3", b"key-2") == 0


def test_round_robin_partitioner() -> None:
    """Test that round-robin partitioner works as intended."""
    partitioner = get_partitioner(topics, "round-robin")

    assert partitioner("topic-1", b"key-1") == 0
    assert partitioner("topic-1", b"key-2") == 1
    assert partitioner("topic-1", b"key-3") == 2
    assert partitioner("topic-1", b"key-4") == 0

    assert partitioner("topic-2", b"key-1") == 0
    assert partitioner("topic-2", b"key-2") == 1
    assert partitioner("topic-2", b"key-3") == 0
    assert partitioner("topic-2", b"key-4") == 1

    assert partitioner("topic-3", b"key-1") == 0
    assert partitioner("topic-3", b"key-2") == 0
    assert partitioner("topic-3", b"key-3") == 0
    assert partitioner("topic-3", b"key-4") == 0


def test_unimplemented_partitioner() -> None:
    """Test that NotImplemented is raised when unknown partitioner strategy is requested."""
    with pytest.raises(NotImplementedError):
        get_partitioner(topics, "unknown")

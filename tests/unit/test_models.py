import pytest

from kafka_mocha.models import KHeader, KRecord, KTopic, KPartition


def test_kheader_creation() -> None:
    """Test Creation of KHeader."""
    header1 = KHeader("key1", "value1".encode("utf-8"))
    header2 = KHeader("key2", "value2".encode("utf-8"))

    assert header1 != header2


def test_krecord_incorrect_creation_error_messages() -> None:
    """Test messages that are thrown when passing incorrect parameters."""
    with pytest.raises(TypeError) as err:
        KRecord("foo", 0, "key1".encode("utf-8"), "value1".encode("utf-8"))
    assert "partition" in err.value.args[0]

    with pytest.raises(TypeError) as err:
        KRecord(0, "bar", "key1".encode("utf-8"), "value1".encode("utf-8"))
    assert "offset" in err.value.args[0]


def test_krecord_creation() -> None:
    """Test Creation of KRecord."""
    header = KHeader("hkey", "hvalue".encode("utf-8"))
    rec1 = KRecord(0, 0, "key1".encode("utf-8"), "value1".encode("utf-8"), (header,))
    rec2 = KRecord(0, 0, "key2".encode("utf-8"), "value2".encode("utf-8"), [header])

    assert rec1 == rec2  # compares only partition and offset
    assert rec1.timestamp != rec2.timestamp


def test_ktopic_creation() -> None:
    """Test Creation of KTopic."""

    with pytest.raises(TypeError) as err:
        KTopic("topic", 0)

    topic1 = KTopic("topic")
    assert len(topic1.partitions) == 1
    assert isinstance(topic1.partitions[0], KPartition)

    topic1 = KTopic("topic", 7)
    assert len(topic1.partitions) == 7
    for partition in topic1.partitions:
        assert isinstance(partition, KPartition)

def test_appending_to_kpartition_() -> None:
    """Test appending Krecords to KPartition."""
    header1 = KHeader("key1", "value1".encode("utf-8"))
    header2 = KHeader("key2", "value2".encode("utf-8"))

    rec1 = KRecord(0, 0, "key1".encode("utf-8"), "value1".encode("utf-8"), (header1,))
    rec2 = KRecord(0, 1, "key2".encode("utf-8"), "value2".encode("utf-8"), [header1, header2])
    rec3 = KRecord(0, 2, "key3".encode("utf-8"), "value3".encode("utf-8"), (header1, header2))
    rec4 = KRecord(0, 3, "key4".encode("utf-8"), "value4".encode("utf-8"), [header2])

    partition = KPartition()
    for rec in [rec1, rec2, rec3, rec4]:
        partition.append(rec)

    assert len(partition._heap) == 4
    for existing, inserted in zip([rec1, rec2, rec3, rec4], partition._heap):
        assert existing.partition == inserted[0]
        assert existing.offset == inserted[1]
        assert existing.key == inserted[2]
        assert existing.value == inserted[3]
        for idx, header in enumerate(existing.headers):
            assert header.key == inserted[4][idx][0]
            assert header.value == inserted[4][idx][1]

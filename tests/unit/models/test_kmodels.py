from typing import Any

import confluent_kafka
import pytest

from kafka_mocha.models.kmodels import CompressionType, KMessage


def test_compression_type() -> None:
    """Test CompressionType Enum."""
    assert CompressionType.NONE.value == "none"
    assert CompressionType.GZIP.value == "gzip"
    assert CompressionType.SNAPPY.value == "snappy"
    assert CompressionType.LZ4.value == "lz4"
    assert CompressionType.ZSTD.value == "zstd"

    assert str(CompressionType.NONE) == "none"
    assert str(CompressionType.GZIP) == "gzip"
    assert str(CompressionType.SNAPPY) == "snappy"
    assert str(CompressionType.LZ4) == "lz4"
    assert str(CompressionType.ZSTD) == "zstd"


def test_kmessage_incorrect_creation_error_messages() -> None:
    """Test messages that are thrown when passing incorrect parameters."""
    with pytest.raises(TypeError) as err:
        KMessage(1.7, 1, "key1".encode("utf-8"), "value1".encode("utf-8"))
    assert "topic" in err.value.args[0].lower()

    with pytest.raises(ValueError) as err:
        KMessage("topic with space", 1, "key1".encode("utf-8"), "value1".encode("utf-8"))
    assert "topic" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", "2", "key1".encode("utf-8"), "value1".encode("utf-8"))
    assert "partition" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", 0, 0, "value1".encode("utf-8"))
    assert "key" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", 0, "key1".encode("utf-8"), 0)
    assert "value" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", 0, b"key1", b"value1", [("h-key", "h-value")])
    assert "headers" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", 0, b"key1", b"value1", [{"h-key": 2}])
    assert "headers" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", 0, b"key1", b"value1", [{2: "h-val"}])
    assert "headers" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", 0, b"key1", b"value1", [2, b"h-value"])
    assert "headers" in err.value.args[0].lower()

    with pytest.raises(ValueError) as err:
        KMessage("topic", 0, b"key1", b"value1", [("h-key", b"h-value")], -20)
    assert "timestamp" in err.value.args[0].lower()

    with pytest.raises(ValueError) as err:
        KMessage("topic", 0, b"key1", b"value1", [("h-key", b"h-value")], ("created", 0))
    assert "timestamp" in err.value.args[0].lower()

    with pytest.raises(TypeError) as err:
        KMessage("topic", 0, b"key1", b"value1", [("h-key", b"h-value")], (0, 1), offset="dupa")
    assert "offset" in err.value.args[0].lower()


@pytest.mark.parametrize("key", [None, "key", "key".encode("utf-8")])
@pytest.mark.parametrize("value", [None, "key", "key".encode("utf-8")])
def test_kmessage_creation_happy_path(key: Any, value: Any) -> None:
    """Test Creation of KMessage."""
    message = KMessage(
        "topic",
        0,
        key,
        value,
        [("h-key", "h-value".encode("utf-8"))],
        (7, confluent_kafka.TIMESTAMP_NOT_AVAILABLE),
        offset=0,
    )

    assert message.topic() == "topic"
    assert message.partition() == 0
    assert message.key() == key
    assert message.value(None) == value
    assert message.headers() == [("h-key", "h-value".encode("utf-8"))]
    assert message.timestamp() == (confluent_kafka.TIMESTAMP_NOT_AVAILABLE, 7)
    assert message.offset() == 0
    assert message.on_delivery is None
    assert message._pid is None
    assert message._error is None


def test_kmessage_setters() -> None:
    """Test KMessage setters."""
    message = KMessage("topic", on_delivery=lambda err, msg: None)

    assert message.topic() == "topic"
    assert message.partition() is None
    assert message.key() is None
    assert message.value(None) is None
    assert message.headers() is None
    assert message.timestamp() == (confluent_kafka.TIMESTAMP_CREATE_TIME, -1)
    assert message.offset() is None
    assert message.on_delivery is not None
    assert message._pid is None
    assert message.error() is None

    message.set_partition(7)
    message.set_key("set-key".encode("utf-8"))
    message.set_value("set-value".encode("utf-8"))
    message.set_headers([("h-key-1", "h-value-1".encode("utf-8")), ("h-key-2", None)])
    message.set_timestamp(7, confluent_kafka.TIMESTAMP_LOG_APPEND_TIME)
    message.set_offset(100)
    message.set_pid(666)
    message.set_error(confluent_kafka.KafkaError._STATE, "Operation not valid in state Ready", fatal=True)

    assert message.partition() == 7
    assert message.key() == "set-key".encode("utf-8")
    assert message.value(None) == "set-value".encode("utf-8")
    assert message.headers()[0][0] == "h-key-1"
    assert message.headers()[0][1] == "h-value-1".encode("utf-8")
    assert message.headers()[1][0] == "h-key-2"
    assert message.headers()[1][1] is None
    assert message.timestamp() == (confluent_kafka.TIMESTAMP_LOG_APPEND_TIME, 7)
    assert message.offset() == 100
    assert message._pid == 666
    assert message._error == confluent_kafka.KafkaError(
        confluent_kafka.KafkaError._STATE, "Operation not valid in state Ready", fatal=True
    )

from enum import Enum, auto
from typing import Any, Callable, Optional

import confluent_kafka


class CompressionType(Enum):
    """https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html#compression-type"""

    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    NONE = auto()
    GZIP = auto()
    SNAPPY = auto()
    LZ4 = auto()
    ZSTD = auto()

    def __str__(self) -> str:
        return str(self.value)


class KMessage:
    """This class is to copy behavior of confluent_kafka.Message class."""

    def __init__(
        self,
        topic: str,
        partition: Optional[int] = None,
        key: Optional[str | bytes] = None,
        value: Optional[str | bytes] = None,
        headers: (
            Optional[list[tuple[str, bytes]]]
            | Optional[tuple[tuple[str, bytes], ...]]
            | Optional[dict[str, str | bytes | None]]
        ) = None,
        timestamp: int | tuple[int, int] = (-1, confluent_kafka.TIMESTAMP_CREATE_TIME),
        *,
        offset: Optional[int] = None,
        on_delivery: Optional[Callable[[Any, Any], None]] = None,
        compression_type: CompressionType = CompressionType.NONE,
        pid: Optional[int] = None,
        marker: bool = False,
    ):
        self._check_topic(topic)
        self.check_partition_offset(partition, allow_none=True)
        self._check_key_value(key)
        self._check_key_value(value)
        self._check_headers(headers)
        self.check_timestamp(timestamp)
        self.check_partition_offset(offset, allow_none=True)

        self._topic: str = topic
        self._partition: Optional[int] = partition
        self._key: Optional[str | bytes] = key
        self._value: Optional[str | bytes] = value
        self._headers: Optional[list[tuple[str, bytes]]] = headers
        if isinstance(timestamp, int):
            self._timestamp = (timestamp, confluent_kafka.TIMESTAMP_CREATE_TIME)
        else:
            self._timestamp = timestamp
        self._offset: Optional[int] = offset
        self._compression_type: CompressionType = compression_type
        self._pid: Optional[int] = pid
        self._marker: bool = marker
        self._error: Optional[confluent_kafka.KafkaError] = None
        self.on_delivery: Optional[Callable[[Any, Any], None]] = on_delivery

    @staticmethod
    def _check_topic(topic: str):
        """Check that topic is a string."""
        if not isinstance(topic, str):
            raise TypeError("Message's topic must be a string")
        elif " " in topic:
            raise ValueError("Topic name cannot contain spaces")

    @staticmethod
    def _check_key_value(obj: Optional[str | bytes]):
        """Check that key/value is a string or bytes."""
        if obj is not None and not isinstance(obj, str) and not isinstance(obj, bytes):
            raise TypeError("Message's key/value must be a string or bytes")

    @staticmethod
    def _check_headers(headers):
        """Check that headers are a list of tuples or a tuple of tuples."""
        if headers is None:
            return
        elif isinstance(headers, list) or isinstance(headers, tuple):
            for header in headers:
                if not isinstance(header, tuple):
                    raise TypeError("Message's headers must be a list (or tuple) of tuples")
                if not isinstance(header[0], str):
                    raise TypeError("Message's headers' keys must be strings")
                if not isinstance(header[1], bytes):
                    raise TypeError("Message's headers' values must be bytes")

        elif isinstance(headers, dict):
            for key, val in headers.items():
                if not isinstance(key, str):
                    raise TypeError("Message's header's key must be a string")
                if val is not None and not isinstance(val, (str, bytes)):
                    raise TypeError("Message's header's value must be a string or bytes or None")
        else:
            raise TypeError("Message's headers must be a list or tuple")

    @staticmethod
    def check_partition_offset(obj: Optional[int], allow_none: bool = False):
        """Check that partition/offset is an integer."""
        if obj is None and not allow_none:
            raise ValueError("Partition/Offset cannot be None on assignment")
        elif obj is not None and not isinstance(obj, int):
            raise TypeError("Partition/Offset must be an integer")
        elif isinstance(obj, int) and obj < -1:
            raise ValueError("Partition/Offset must be a positive integer")

    @staticmethod
    def check_timestamp(timestamp: int | tuple[int, int]):
        """Check that timestamp is a tuple of two integers."""
        if isinstance(timestamp, int):
            if timestamp < -1:
                raise ValueError("Timestamp must be a positive integer")
        elif isinstance(timestamp, tuple):
            if len(timestamp) != 2:
                raise ValueError("Timestamp must be a tuple of two integers")
            elif not isinstance(timestamp[0], int) or timestamp[0] < -1:
                raise ValueError("Timestamp must be a positive integer")
            elif timestamp[1] not in (
                confluent_kafka.TIMESTAMP_NOT_AVAILABLE,
                confluent_kafka.TIMESTAMP_CREATE_TIME,
                confluent_kafka.TIMESTAMP_LOG_APPEND_TIME,
            ):
                raise ValueError("Timestamp type must be either 0, 1, 2")
        else:
            raise TypeError("Timestamp must be an integer or a tuple of two integers")

    def error(self) -> Optional[confluent_kafka.KafkaError]:
        if self._error:
            return confluent_kafka.KafkaError(self._error)
        return None

    def headers(self) -> Optional[list[tuple[str, bytes]]]:
        return self._headers

    def key(self) -> Optional[str | bytes]:
        return self._key

    def value(self, payload) -> Optional[str | bytes]:
        return self._value

    def offset(self) -> Optional[int]:
        return self._offset

    def partition(self) -> Optional[int]:
        return self._partition

    def timestamp(self) -> tuple[int, int]:
        return self._timestamp[1], self._timestamp[0]

    def topic(self) -> Optional[str]:
        return self._topic

    def latency(self, *args, **kwargs) -> Optional[float]:
        return None

    def leader_epoch(self, *args, **kwargs) -> Optional[int]:
        return None

    def set_headers(self, *args, **kwargs) -> None:
        """
        Set the field 'Message.key' with new value.

        Signature matches confluent_kafka.Message.set_headers
        """
        self._check_headers(args[0])
        self._headers = args[0]

    def set_key(self, *args, **kwargs) -> None:
        """
        Set the field 'Message.value' with new value.

        Signature matches confluent_kafka.Message.set_key
        """
        self._check_key_value(args[0])
        self._key = args[0].encode() if isinstance(args[0], str) else args[0]

    def set_value(self, *args, **kwargs) -> None:
        """
        Set the field 'Message.value' with new value.

        Signature matches confluent_kafka.Message.set_value
        """
        self._check_key_value(args[0])
        self._value = args[0].encode() if isinstance(args[0], str) else args[0]

    def set_partition(self, partition: int) -> None:
        """Set the field 'Message.partition' with new value."""
        self.check_partition_offset(partition, allow_none=False)
        self._partition = partition

    def set_offset(self, offset: int) -> None:
        """Set the field 'Message.offset' with new value."""
        self.check_partition_offset(offset, allow_none=False)
        self._offset = offset

    def set_timestamp(self, timestamp_ms: int, timestamp_type: int = confluent_kafka.TIMESTAMP_CREATE_TIME) -> None:
        """Set the field 'Message.timestamp' with new value."""
        self.check_timestamp((timestamp_ms, timestamp_type))
        self._timestamp = (timestamp_ms, timestamp_type)

    def set_pid(self, pid: int) -> None:
        """Set the field 'Message.pid' with new value."""
        self._pid = pid

    def set_error(self, state: int, msg: str, fatal: bool = True) -> None:
        """Set the field 'Message.error' with new value."""
        self._error = confluent_kafka.KafkaError(state, msg, fatal=fatal)

    def __str__(self) -> str:
        return (
            f"KMessage(topic={self._topic}, partition={self._partition}, offset={self._offset}, key={self._key}, "
            f"value={self._value}, headers={self._headers}, timestamp={self._timestamp})"
        )

    def __len__(self, *args, **kwargs) -> int:
        header_acc = 0
        if self._headers:
            if isinstance(self._headers, dict):
                for k, v in self._headers.items():
                    header_acc += len(k) + len(v)
            else:
                for header in self._headers:
                    header_acc += len(header[0]) + len(header[1])
        key_acc = len(self._key) if self._key else 0
        value_acc = len(self._value) if self._value else 0
        return key_acc + value_acc + header_acc


class KPartition:
    """Dataclass mimicking Kafka partition"""

    def __init__(self):
        self._heap: list[KMessage] = []

    def append(self, message: KMessage) -> None:
        self._heap.append(message)

    def get(self, offset: int = 0, batch_size: int = 1) -> list[KMessage]:
        return self._heap[offset:batch_size]

    def __len__(self) -> int:
        return len(self._heap)


class KTopic:
    """Dataclass mimicking Kafka topic"""

    def __init__(self, name: str, partition_no: int = 1, config: Optional[dict[str, Any]] = None):
        if not (isinstance(partition_no, int) and partition_no > 0):
            raise TypeError("Topic's partition number must be integer greater than 0")
        self.partition_no = partition_no
        self.partitions = [KPartition() for _ in range(partition_no)]
        self.name = name
        self.config = config

    @classmethod
    def from_env(cls, env_config: str) -> "KTopic":
        try:
            name, partition_no = env_config.split(":")
        except ValueError:
            name, partition_no = env_config, 1
        return cls(name, int(partition_no))

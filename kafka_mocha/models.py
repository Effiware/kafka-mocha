from abc import ABC
from dataclasses import asdict, astuple, dataclass, field, replace
from enum import Enum, auto
from heapq import heappush
from typing import Any, Callable, Literal, Optional

from confluent_kafka import TIMESTAMP_CREATE_TIME


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


@dataclass(eq=False)
class KHeader:
    """Dataclass mimicking Kafka record header"""

    key: str
    value: bytes

    def __post_init__(self):
        if not isinstance(self.value, bytes):
            raise TypeError("Value must be bytes")

    @classmethod
    def from_tuple(cls, header: tuple) -> "KHeader":
        return cls(header[0], header[1])


@dataclass(eq=False)
class ABCMessage(ABC):
    topic: str
    partition: int
    key: bytes
    value: bytes
    headers: Optional[tuple[KHeader, ...] | list[KHeader]] = field(default=None, compare=False)
    timestamp: tuple[int, int] = field(default=(TIMESTAMP_CREATE_TIME, -1), kw_only=True)
    compression_type: CompressionType = field(default=CompressionType.NONE, compare=False, kw_only=True)
    marker: bool = field(default=False, kw_only=True)

    def __post_init__(self):
        if not isinstance(self.key, bytes):
            raise TypeError("Message's key must be bytes")
        if not isinstance(self.value, bytes):
            raise TypeError("Message's value must be bytes")
        if self.headers:
            if not isinstance(self.headers, tuple) and not isinstance(self.headers, list):
                raise TypeError("Message's headers must be a tuple or a list")
        if self.__class__ == ABCMessage:
            raise TypeError("Cannot instantiate an abstract class.")


@dataclass(eq=False)
class PMessage(ABCMessage):
    """Dataclass mimicking producer message"""

    on_delivery: Optional[Callable[[Any, Any], None]] = field(default=None, kw_only=True)
    pid: Optional[int] = field(default=None, kw_only=True)

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.partition, int) or self.partition < -1:  # -1 is a flag to run partitioner
            raise TypeError("PMessage's partition must be an unsigned integer (or -1).")

    @classmethod
    def from_producer_data(cls, *, headers: tuple | list, timestamp: int, **kwargs) -> "PMessage":
        k_headers = [KHeader.from_tuple(header) for header in headers] if headers else []
        _key = kwargs.pop("key", None)
        _value = kwargs.pop("value", None)
        kwargs["key"] = _key.encode() if isinstance(_key, str) else _key
        kwargs["value"] = _value.encode() if isinstance(_value, str) else _value
        if timestamp != 0:
            return cls(headers=k_headers, timestamp=(TIMESTAMP_CREATE_TIME, timestamp), **kwargs)
        return cls(headers=k_headers, **kwargs)


@dataclass(eq=False)
class KRecord(ABCMessage):
    """Dataclass mimicking Kafka record"""

    offset: int = field(default=-1, kw_only=True)
    pid: Optional[int] = field(default=None, kw_only=True)

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.partition, int) or self.partition < 0:
            raise TypeError("Record's partition must be an unsigned integer")
        if not isinstance(self.offset, int) or self.offset < 0:
            raise TypeError("Record's offset must be unsigned integer")

    def as_tuple(self) -> tuple:
        if isinstance(self.headers, list):
            copy = replace(self, headers=tuple(self.headers))
            return astuple(copy)
        return astuple(self)

    @classmethod
    def from_pmessage(
        cls,
        pmessage: PMessage,
        offset: int,
        ts_type: Literal["EventTime", "LogAppendTime"] = "EventTime",
        ts: Optional[int] = None,
    ) -> "KRecord":
        """Create KRecord from PMessage (producer message) depending on configuration"""
        pmessage_dict = asdict(pmessage)
        del pmessage_dict["on_delivery"]
        if ts_type == "LogAppendTime" and ts is None:
            raise TypeError(f"Timestamp must be provided when {ts_type} is used.")
        elif ts_type == "LogAppendTime":
            cls(**pmessage_dict, offset=offset, timestamp=ts)
        return cls(**pmessage_dict, offset=offset)

    def __eq__(self, other) -> bool:
        """Record is unambiguously determined by partition and offset (and pid if exists)."""
        return self.offset == other.offset and self.partition == other.partition

    def __str__(self) -> str:
        return (
            f"("
            f"partition={self.partition}, "
            f"offset={self.offset}, "
            f"key={self.key}, "
            f"value={self.value}, "
            # f"timestamp={datetime.fromtimestamp(self.timestamp).isoformat()}, "
            f"headers={self.headers})"
            f")"
        )


class KPartition:
    """Dataclass mimicking Kafka partition"""

    def __init__(self):
        self._heap = []

    def append(self, record: KRecord) -> None:
        heappush(self._heap, record.as_tuple())

    def get(self, offset: int = 0, batch_size: int = 1) -> list[KRecord]:
        return self._heap[offset:batch_size]

    def __len__(self) -> int:
        return len(self._heap)


@dataclass(frozen=True)
class KTopic:
    """Dataclass mimicking Kafka topic"""

    name: str
    partition_no: int = field(default=1)
    partitions: list[KPartition] = field(init=False, default_factory=list, repr=False)
    config: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if not (isinstance(self.partition_no, int) and self.partition_no > 0):
            raise TypeError("Topic's partition number must be integer greater than 0")
        [self.partitions.append(KPartition()) for _ in range(self.partition_no)]

    @classmethod
    def from_env(cls, env_config: str) -> "KTopic":
        try:
            name, partition_no = env_config.split(":")
        except ValueError:
            name, partition_no = env_config, 1
        return cls(name, int(partition_no))

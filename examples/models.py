from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


def dict_factory(data) -> dict:
    """Converts dataclass to dictionary with custom conversion for UUID, Enum and datetime."""
    def convert(obj):
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return int(obj.timestamp() * 1000)
        return obj
    return {k: convert(v) for k, v in data}


class SubscriptionType(str, Enum):
    FREE = "FREE"
    LITE = "LITE"
    PRO = "PRO"


@dataclass
class EventEnvelope:
    envelope_id: UUID = field(default_factory=uuid4)
    event_timestamp: datetime = field(default_factory=datetime.now)
    app_name: str = field(default="kafka_mocha_examples")
    app_version: str = field(default="1.0.0")


@dataclass
class UserRegistered:
    user_id: UUID
    user_name: str
    user_last_name: str
    is_new_user: bool
    subscription_type: SubscriptionType
    registration_timestamp: datetime
    score: float
    envelope: EventEnvelope

    def to_dict(self):
        return asdict(self, dict_factory=dict_factory)

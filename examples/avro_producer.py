import doctest
import json
from datetime import datetime
from uuid import uuid4

import confluent_kafka
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField, StringSerializer

from examples.models import UserRegistered, EventEnvelope, SubscriptionType
from kafka_mocha import mock_producer
from kafka_mocha.schema_registry.mock_schema_registry_client import MockSchemaRegistryClient

TOPIC_NAME = "avro-topic"


@mock_producer(loglevel="DEBUG")
def with_auto_register_schema():
    """Use Mock Schema Registry client to auto-register the schema, serialise and produce AVRO message.

    >>> with_auto_register_schema()
    AVRO message delivered (auto.register.schemas)
    """
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})
    schema_registry = MockSchemaRegistryClient({"url": "http://localhost:8081"})
    with open("schemas/user-registered.avsc", "r") as f:
        avro_schema = json.loads(f.read())
        avro_schema_str = json.dumps(avro_schema)

    string_serializer = StringSerializer()
    avro_serializer = AvroSerializer(
        schema_registry,
        avro_schema_str,
        conf={"auto.register.schemas": True},
    )
    user_id = uuid4()
    event = UserRegistered(user_id, "John", "Doe", True, SubscriptionType.PRO, datetime.now(), 0.0, EventEnvelope())

    producer.produce(
        TOPIC_NAME,
        string_serializer(str(user_id)),
        avro_serializer(event.to_dict(), SerializationContext(TOPIC_NAME, MessageField.VALUE)),
        on_delivery=lambda err, msg: print("AVRO message delivered (auto.register.schemas)"),
    )
    producer.flush()


if __name__ == "__main__":
    doctest.testmod(verbose=True)

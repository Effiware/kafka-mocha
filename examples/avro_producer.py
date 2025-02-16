import doctest
import json
from datetime import datetime
from uuid import uuid4

import confluent_kafka
import confluent_kafka.schema_registry
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField, StringSerializer

from examples.models import UserRegistered, EventEnvelope, SubscriptionType
from kafka_mocha import mock_producer
from kafka_mocha.schema_registry import mock_schema_registry
from kafka_mocha.schema_registry.mock_schema_registry_client import MockSchemaRegistryClient


@mock_schema_registry(loglevel="INFO", register_schemas=["schemas/user-registered.avsc"])
@mock_producer(output={"format": "csv"})
def use_latest_registered_schema():
    """
    Use Mock Schema Registry client to find latest schema registered for given subject, serialize message with this
    schema and produce message to Kafka.

    >>> use_latest_registered_schema()
    AVRO message delivered (auto.register.schemas = False, use.latest.version = True)
    """
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})
    schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})

    string_serializer = StringSerializer()
    avro_serializer = AvroSerializer(schema_registry, conf={"auto.register.schemas": False, "use.latest.version": True})

    user_id = uuid4()
    event = UserRegistered(user_id, "John", "Doe", True, SubscriptionType.PRO, datetime.now(), 0.0, EventEnvelope())

    producer.produce(
        "user-registered.avsc",
        string_serializer(str(user_id)),
        avro_serializer(event.to_dict(), SerializationContext("user-registered.avsc", MessageField.VALUE)),
        on_delivery=lambda err, msg: print(
            "AVRO message delivered (auto.register.schemas = False, use.latest.version = True)"
        ),
    )
    producer.flush()


@mock_producer(loglevel="DEBUG")
def auto_register_schema():
    """Use Mock Schema Registry client to auto-register the schema, serialise and produce AVRO message.

    >>> auto_register_schema()
    AVRO message delivered (auto.register.schemas = True)
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
        "user-registered.avsc",
        string_serializer(str(user_id)),
        avro_serializer(event.to_dict(), SerializationContext("user-registered.avsc", MessageField.VALUE)),
        on_delivery=lambda err, msg: print("AVRO message delivered (auto.register.schemas = True)"),
    )
    producer.flush()


@mock_schema_registry(register_schemas=["schemas/user-registered.avsc"])
@mock_producer()
def use_any_registered_schema():
    """
    Use Mock Schema Registry client to find latest schema registered for given subject, serialize message with this
    schema and produce message to Kafka.

    >>> use_any_registered_schema()
    AVRO message delivered (auto.register.schemas = False, use.latest.version = False)
    """
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})
    schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})
    with open("schemas/user-registered.avsc", "r") as f:
        avro_schema = json.loads(f.read())
        avro_schema_str = json.dumps(avro_schema)

    string_serializer = StringSerializer()
    avro_serializer = AvroSerializer(
        schema_registry, avro_schema_str, conf={"auto.register.schemas": False, "use.latest.version": False}
    )

    user_id = uuid4()
    event = UserRegistered(user_id, "John", "Doe", True, SubscriptionType.PRO, datetime.now(), 0.0, EventEnvelope())

    producer.produce(
        "user-registered.avsc",
        string_serializer(str(user_id)),
        avro_serializer(event.to_dict(), SerializationContext("user-registered.avsc", MessageField.VALUE)),
        on_delivery=lambda err, msg: print(
            "AVRO message delivered (auto.register.schemas = False, use.latest.version = False)"
        ),
    )
    producer.flush()


if __name__ == "__main__":
    doctest.testmod(verbose=True)

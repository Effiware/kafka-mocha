import doctest
import json
import os
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

TOPIC_NAME = "user-registered.avsc"
LOCAL_SCHEMA = str(os.path.join(os.path.dirname(__file__), "schemas/user-registered.avsc"))


@mock_schema_registry(loglevel="INFO", register_schemas=[LOCAL_SCHEMA])
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
        topic=TOPIC_NAME,
        key=string_serializer(str(user_id)),
        value=avro_serializer(event.to_dict(), SerializationContext(TOPIC_NAME, MessageField.VALUE)),
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
    with open(LOCAL_SCHEMA, "r") as f:
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
        topic=TOPIC_NAME,
        key=string_serializer(str(user_id)),
        value=avro_serializer(event.to_dict(), SerializationContext(TOPIC_NAME, MessageField.VALUE)),
        on_delivery=lambda err, msg: print("AVRO message delivered (auto.register.schemas = True)"),
    )
    producer.flush()


@mock_schema_registry(register_schemas=[LOCAL_SCHEMA])
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
    with open(LOCAL_SCHEMA, "r") as f:
        avro_schema = json.loads(f.read())
        avro_schema_str = json.dumps(avro_schema)

    string_serializer = StringSerializer()
    avro_serializer = AvroSerializer(
        schema_registry, avro_schema_str, conf={"auto.register.schemas": False, "use.latest.version": False}
    )

    user_id = uuid4()
    event = UserRegistered(user_id, "John", "Doe", True, SubscriptionType.PRO, datetime.now(), 0.0, EventEnvelope())

    producer.produce(
        topic=TOPIC_NAME,
        key=string_serializer(str(user_id)),
        value=avro_serializer(event.to_dict(), SerializationContext(TOPIC_NAME, MessageField.VALUE)),
        on_delivery=lambda err, msg: print(
            "AVRO message delivered (auto.register.schemas = False, use.latest.version = False)"
        ),
    )
    producer.flush()


def missing_schema():
    """
    Mock Schema Registry client with also checks configuration.

    >>> missing_schema()
    Traceback (most recent call last):
    ...
    kafka_mocha.schema_registry.exceptions.SchemaRegistryError: Schema Not Found (HTTP status code 404, SR code 40400)
    """
    schema_registry = MockSchemaRegistryClient({"url": "http://localhost:8081"})
    with open(LOCAL_SCHEMA, "r") as f:
        avro_schema = json.loads(f.read())
        avro_schema_str = json.dumps(avro_schema)

    avro_serializer = AvroSerializer(
        schema_registry, avro_schema_str, conf={"auto.register.schemas": False, "use.latest.version": False}
    )
    user_id = uuid4()
    event = UserRegistered(user_id, "John", "Doe", True, SubscriptionType.PRO, datetime.now(), 0.0, EventEnvelope())

    avro_serializer(event.to_dict(), SerializationContext(TOPIC_NAME, MessageField.VALUE))


if __name__ == "__main__":
    doctest.testmod(verbose=True)

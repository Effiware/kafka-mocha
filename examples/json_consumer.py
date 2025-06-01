import doctest
import json
import os

import confluent_kafka
import confluent_kafka.schema_registry
from confluent_kafka.schema_registry.json_schema import JSONDeserializer
from confluent_kafka.serialization import MessageField, SerializationContext, StringDeserializer

from kafka_mocha import mock_consumer
from kafka_mocha.schema_registry import mock_schema_registry

TOPIC_NAME = "user-registered-cons-json"
LOCAL_SCHEMA = str(os.path.join(os.path.dirname(__file__), "schemas/user-registered.json"))
LOCAL_INPUT = str(os.path.join(os.path.dirname(__file__), "inputs/users-registrations-in-json.json"))


@mock_schema_registry(register_schemas=[{"source": LOCAL_SCHEMA, "subject": TOPIC_NAME + "-value"}])
@mock_consumer(inputs=[{"source": LOCAL_INPUT, "topic": TOPIC_NAME, "serialize": True}])
def consume_preloaded_json_serialized_messages():
    """Mock consumer will consume preloaded messages (serialized to JSON) from the topic.

    >>> consume_preloaded_json_serialized_messages()
    Consumed message: key: '52436bdf-9303-4335-939b-6f5889c14d02', value: '{"user_id": "52436bdf-9303-4335-939b-6f5889c14d02", "user_name": "Jannet", ...'
    Consumed message: key: 'dd6b9cfd-135e-4b5b-a34c-a0ecd7a2b563', value: '{"user_id": "dd6b9cfd-135e-4b5b-a34c-a0ecd7a2b563", "user_name": "Johnny", ...'
    Consumed message: key: 'e14365d3-fba9-4c73-88ae-7c53f7f07ea8', value: '{"user_id": "e14365d3-fba9-4c73-88ae-7c53f7f07ea8", "user_name": "Andrea", ...'
    """
    schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group-json-serialized",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([TOPIC_NAME])
    key_deserializer = StringDeserializer()
    value_deserializer = JSONDeserializer(
        schema_registry_client=schema_registry,
        schema_str=None,
        conf={"use.latest.version": True},
    )

    msgs = consumer.consume(10, timeout=0.5)
    for msg in msgs:
        if msg.error():
            raise confluent_kafka.KafkaException(msg.error())
        else:
            key = key_deserializer(msg.key())
            value = value_deserializer(msg.value(None), SerializationContext(TOPIC_NAME, MessageField.VALUE))
            value_str = json.dumps(value)
            print(f"Consumed message: key: '{key}', value: '{value_str[:75]}...'")
    consumer.close()


if __name__ == "__main__":
    doctest.testmod(verbose=True)

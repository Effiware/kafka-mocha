import doctest
import os

import confluent_kafka
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext

from kafka_mocha import mock_consumer, mock_producer
from kafka_mocha.schema_registry import mock_schema_registry

INPUT_TOPIC = "user-registered-cons-avro-2"
OUTPUT_TOPIC = "user-registered-cons-avro-out"
LOCAL_SCHEMA_KEY = str(os.path.join(os.path.dirname(__file__), "schemas/struct-key.avsc"))
LOCAL_SCHEMA_VALUE = str(os.path.join(os.path.dirname(__file__), "schemas/user-registered.avsc"))
LOCAL_INPUT = str(os.path.join(os.path.dirname(__file__), "inputs/users-registrations-in-avro-2.json"))


@mock_schema_registry(
    register_schemas=[
        {"source": LOCAL_SCHEMA_KEY, "subject": INPUT_TOPIC + "-key"},
        {"source": LOCAL_SCHEMA_VALUE, "subject": INPUT_TOPIC + "-value"},
        {"source": LOCAL_SCHEMA_KEY, "subject": OUTPUT_TOPIC + "-key"},
        {"source": LOCAL_SCHEMA_VALUE, "subject": OUTPUT_TOPIC + "-value"},
    ]
)
@mock_consumer(inputs=[{"source": LOCAL_INPUT, "topic": INPUT_TOPIC, "serialize": True}])
@mock_producer(output={"format": "csv"})
def transact_consume_preloaded_messages_and_produce():
    """
    Mock consumer will consume AVRO preloaded messages from the topic and mock producer will produce them to other topic

    >>> transact_consume_preloaded_messages_and_produce()
    Consumed message: key (raw): b'52436bdf-9303-4335-939b-6f5889c14d02\x02(registration-service', value (raw): b'52436bdf-9303-4335-939b-6f5889c14d02\x0cJannet'...
    Produced message: key (raw): b'52436bdf-9303-4335-939b-6f5889c14d02\x02(registration-service', value (raw): b'52436bdf-9303-4335-939b-6f5889c14d02\x0cJANNET'...
    Consumed message: key (raw): b'dd6b9cfd-135e-4b5b-a34c-a0ecd7a2b563\x02(registration-service', value (raw): b'dd6b9cfd-135e-4b5b-a34c-a0ecd7a2b563\x0cJohnny'...
    Produced message: key (raw): b'dd6b9cfd-135e-4b5b-a34c-a0ecd7a2b563\x02(registration-service', value (raw): b'dd6b9cfd-135e-4b5b-a34c-a0ecd7a2b563\x0cJOHNNY'...
    Consumed message: key (raw): b'e14365d3-fba9-4c73-88ae-7c53f7f07ea8\x02(registration-service', value (raw): b'e14365d3-fba9-4c73-88ae-7c53f7f07ea8\x0cAndrea'...
    Produced message: key (raw): b'e14365d3-fba9-4c73-88ae-7c53f7f07ea8\x02(registration-service', value (raw): b'e14365d3-fba9-4c73-88ae-7c53f7f07ea8\x0cANDREA'...
    """
    schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group-consume",
            "auto.offset.reset": "earliest",
        }
    )
    producer = confluent_kafka.Producer(
        {
            "bootstrap.servers": "localhost:9092",
            "enable.idempotence": True,
            "transactional.id": "test-transact-prosumer-id",
        }
    )

    avro_deserializer = AvroDeserializer(schema_registry, conf={"use.latest.version": True})
    avro_serializer = AvroSerializer(schema_registry, conf={"auto.register.schemas": False, "use.latest.version": True})

    consumer.subscribe([INPUT_TOPIC])
    producer.init_transactions()

    poll_num = 0
    producer.begin_transaction()
    try:
        while poll_num < 10:
            producer.poll(0)
            msg_in = consumer.poll(timeout=0.3)
            if msg_in is None:
                poll_num += 1
                continue
            if msg_in.error():
                raise confluent_kafka.KafkaException(msg_in.error())
            else:
                value_des = avro_deserializer(msg_in.value(None), SerializationContext(INPUT_TOPIC, MessageField.VALUE))
                print(
                    f"Consumed message: key (raw): b'{(msg_in.key()[6:]).decode()}', "
                    f"value (raw): b'{(msg_in.value(None)[6:49]).decode()}'..."
                )

                value_des["user_name"] = value_des["user_name"].upper()
                value_ser = avro_serializer(value_des, SerializationContext(OUTPUT_TOPIC, MessageField.VALUE))
                producer.produce(
                    OUTPUT_TOPIC,
                    key=msg_in.key(),
                    value=value_ser,
                    on_delivery=lambda e, m: print(
                        f"Produced message: key (raw): b'{(m.key()[6:]).decode()}', "
                        f"value (raw): b'{(m.value(None)[6:49]).decode()}'..."
                        if not e
                        else f"Error: {e}"
                    ),
                )

                producer.send_offsets_to_transaction(
                    consumer.position(consumer.assignment()), consumer.consumer_group_metadata()
                )
                producer.commit_transaction()

                producer.begin_transaction()
                poll_num += 1

    except Exception as ex:
        print(f"An error occurred: {ex}")
        producer.abort_transaction()
    else:
        producer.send_offsets_to_transaction(
            consumer.position(consumer.assignment()), consumer.consumer_group_metadata()
        )
        producer.commit_transaction()
    finally:
        consumer.close()


if __name__ == "__main__":
    doctest.testmod(verbose=True)

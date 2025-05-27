import doctest
import os

import confluent_kafka

from kafka_mocha import mock_consumer, mock_producer

INPUT_TOPIC_NAME = "test-simple-prosumer-topic-in"
OUTPUT_TOPIC_NAME = "test-simple-prosumer-topic-out"
LOCAL_INPUT = str(os.path.join(os.path.dirname(__file__), "inputs/users-registrations.json"))


@mock_consumer(inputs=[{"source": LOCAL_INPUT, "topic": INPUT_TOPIC_NAME}])
@mock_producer(output={"format": "csv"})
def consume_preloaded_messages_and_produce():
    """Mock consumer will consume preloaded messages from the topic and mock producer will produce them to other topic.

    >>> consume_preloaded_messages_and_produce()
    Consumed message (test-simple-prosumer-topic-in): key: 856254a0-7ec9-47cb-8f61-fd51e92eeb96, value: {"user_id": "856254a0-7ec9-47cb-8f61-fd51e92eeb96", "user_name": "Albert", ...
    Consumed message (test-simple-prosumer-topic-in): key: 237a917d-269f-4e20-96f3-0c4c43ac0d9c, value: {"user_id": "237a917d-269f-4e20-96f3-0c4c43ac0d9c", "user_name": "Johnny", ...
    Consumed message (test-simple-prosumer-topic-in): key: d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6, value: {"user_id": "d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6", "user_name": "Dakota", ...
    Produced message (test-simple-prosumer-topic-out): key: 856254a0-7ec9-47cb-8f61-fd51e92eeb96, value: USER_REGISTERED
    Produced message (test-simple-prosumer-topic-out): key: 237a917d-269f-4e20-96f3-0c4c43ac0d9c, value: USER_REGISTERED
    Produced message (test-simple-prosumer-topic-out): key: d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6, value: USER_REGISTERED
    """
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group-consume",
            "auto.offset.reset": "earliest",
        }
    )
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})
    consumer.subscribe([INPUT_TOPIC_NAME])

    msgs = consumer.consume(10, timeout=0.5)
    for msg in msgs:
        if msg.error():
            raise confluent_kafka.KafkaException(msg.error())
        else:
            print(f"Consumed message ({msg.topic()}): key: {msg.key()}, value: {msg.value(None)[:75]}...")
            producer.produce(
                OUTPUT_TOPIC_NAME,
                key=msg.key(),
                value="USER_REGISTERED",
                on_delivery=lambda e, m: print(
                    f"Produced message ({m.topic()}): key: {m.key()}, value: {m.value(None)}"
                    if not e
                    else f"Error: {e}"
                ),
            )

    producer.flush()
    consumer.close()


if __name__ == "__main__":
    doctest.testmod(verbose=True)

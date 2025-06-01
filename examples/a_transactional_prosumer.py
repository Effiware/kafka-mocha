import doctest
import os

import confluent_kafka

from kafka_mocha import mock_consumer, mock_producer

INPUT_TOPIC_NAME = "test-transact-prosumer-topic-in"
OUTPUT_TOPIC_NAME = "test-transact-prosumer-topic-out"
LOCAL_INPUT = str(os.path.join(os.path.dirname(__file__), "inputs/users-registrations.json"))


@mock_consumer(inputs=[{"source": LOCAL_INPUT, "topic": INPUT_TOPIC_NAME}])
@mock_producer(output={"format": "csv"})
def consume_preloaded_messages_and_produce():
    """Mock consumer will consume preloaded messages from the topic and mock producer will produce them to other topic.

    >>> consume_preloaded_messages_and_produce()
    Consumed message (test-transact-prosumer-topic-in): key: 856254a0-7ec9-47cb-8f61-fd51e92eeb96, value: {"user_id": "856254a0-7ec9-47cb-8f61-fd51e92eeb96", "user_name": "Albert", ...
    Produced message (test-transact-prosumer-topic-out): key: 856254a0-7ec9-47cb-8f61-fd51e92eeb96, value: USER_REGISTERED
    Consumed message (test-transact-prosumer-topic-in): key: 237a917d-269f-4e20-96f3-0c4c43ac0d9c, value: {"user_id": "237a917d-269f-4e20-96f3-0c4c43ac0d9c", "user_name": "Johnny", ...
    Produced message (test-transact-prosumer-topic-out): key: 237a917d-269f-4e20-96f3-0c4c43ac0d9c, value: USER_REGISTERED
    Consumed message (test-transact-prosumer-topic-in): key: d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6, value: {"user_id": "d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6", "user_name": "Dakota", ...
    Produced message (test-transact-prosumer-topic-out): key: d1b2c3d4-e5f6-7a8b-9a0b-c1d2e3f4g5h6, value: USER_REGISTERED
    """
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
    consumer.subscribe([INPUT_TOPIC_NAME])
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
                print(f"Consumed message ({msg_in.topic()}): key: {msg_in.key()}, value: {msg_in.value(None)[:75]}...")
                producer.produce(
                    OUTPUT_TOPIC_NAME,
                    key=msg_in.key(),
                    value="USER_REGISTERED",
                    on_delivery=lambda e, m: print(
                        f"Produced message ({m.topic()}): key: {m.key()}, value: {m.value(None)}"
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

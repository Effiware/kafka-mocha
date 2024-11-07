from time import sleep

from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.kproducer import KProducer


def test_kafka_simulator_bootstrap():
    kafka = KafkaSimulator()
    producer = KProducer({})

    no_msg_to_produce = 1000
    for idx, _ in enumerate(range(no_msg_to_produce)):
        sleep(0.01)
        producer.produce("topic-1", f"key-{idx}".encode(), "value".encode(), on_delivery=lambda *_: None)

    producer._done()

    no_msg_appended = 0
    for topic in kafka.topics:
        for partition in topic.partitions:
            no_msg_appended += len(partition._heap)

    assert kafka is not None
    assert no_msg_appended == no_msg_to_produce
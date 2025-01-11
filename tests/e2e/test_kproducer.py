from confluent_kafka import Producer
from confluent_kafka.admin import ClusterMetadata

from logging import getLogger

logger = getLogger(__name__)


def delivery_report(err, msg):
    """Called once for each message produced to indicate delivery result. Triggered by poll() or flush()."""
    print(err)
    # print(err.__dict__)
    print(msg)
    print(msg.topic())
    if err is not None:
        logger.error("Message delivery failed: {}".format(err))
    else:
        logger.info("Message delivered to {} [{}]".format(msg.topic(), msg.partition()))


def test_e2e_producing_basic_messages():
    """Test producing basic messages."""
    producer = Producer({"bootstrap.servers": "localhost:9092"})

    no_msg_to_produce = 10
    for idx, _ in enumerate(range(no_msg_to_produce)):
        producer.produce("topic-1", "value".encode(), f"key-{idx}".encode(), on_delivery=delivery_report)

    no_msg_to_produce = 10
    for idx, _ in enumerate(range(no_msg_to_produce)):
        producer.produce("topic-1", "value", f"key-{idx}", on_delivery=delivery_report)

    producer.flush()

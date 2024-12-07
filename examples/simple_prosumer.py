from confluent_kafka import Consumer, Producer
from confluent_kafka.serialization import SerializationContext, MessageField


def main(args):
    topic = args.topic
    producer_conf = {
        "bootstrap.servers": args.bootstrap_servers,
        "group.id": args.group,
        "auto.offset.reset": "earliest",
    }

    # consumer = Consumer(consumer_conf)
    # consumer.subscribe([topic])

    producer = Producer(producer_conf)

    while True:
        try:
            msg = producer.poll(5.0)

            if user is not None:
                print(
                    "User record {}: name: {}\n"
                    "\tfavorite_number: {}\n"
                    "\tfavorite_color: {}\n".format(msg.key(), user.name, user.favorite_number, user.favorite_color)
                )
        except KeyboardInterrupt:
            break

    consumer.close()

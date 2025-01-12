"""
Example configuration file. All reused abstractions are kept here.
Below doctests are used jsut to illustrate the usage of the configuration file. Mind that in this case
(without kafka_mocha) it needs Kafka broker running locally.
"""

from datetime import datetime

import confluent_kafka


def handle_produce(topic_name: str):
    """Auxiliary function to abstract message producing for illustration purposes."""

    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})

    i = 3
    while i > 0:
        try:
            producer.poll(3.0)
            producer.produce(
                topic_name,
                datetime.now().isoformat(),
                str(id(producer)),
                on_delivery=lambda err, msg: print("Inner message delivered"),
            )
            producer.flush()
        except KeyboardInterrupt:
            break
        else:
            i -= 1

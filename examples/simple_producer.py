import sys
from datetime import datetime

from confluent_kafka import Producer


def main(args):
    topic = args[1]
    producer = Producer({"bootstrap.servers": "localhost:9092"})

    while True:
        try:
            producer.poll(5.0)
            producer.produce("test-topic", datetime.now().isoformat(), str(id(producer)))
            producer.flush()
            print("Message produced")
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main(sys.argv)

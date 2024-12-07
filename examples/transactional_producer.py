import sys
from datetime import datetime

from confluent_kafka import Producer


def main(args):
    topic = args[1]
    producer = Producer({"bootstrap.servers": "localhost:9092", "transactional.id": "transactional_id"})
    producer.init_transactions()

    while True:
        try:
            producer.begin_transaction()
            producer.poll(5.0)
            producer.produce("test-topic-trans", datetime.now().isoformat(), str(id(producer)))
            producer.commit_transaction()
            print("Message produced")
        except KeyboardInterrupt:
            producer.abort_transaction()
            break


if __name__ == "__main__":
    main(sys.argv)

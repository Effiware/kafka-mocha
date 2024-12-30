from kafka_mocha.wrappers import mock_producer, MockProducer
import sys
from datetime import datetime

# from confluent_kafka import Producer
import confluent_kafka
# from confluent_kafka import Producer



# @mock_producer
@MockProducer()
def main(args):
    topic = args[1]
    # producer = Producer({"bootstrap.servers": "localhost:9092"})
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})

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

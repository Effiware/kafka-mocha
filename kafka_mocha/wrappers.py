from confluent_kafka import Producer as ConfluentProducer
from kafka_mocha.kproducer import KProducer
from functools import wraps


def mock_producer(cls):
    """Wrapp Kafka Producer class and return KProducer (mock)

    :param cls:
    :return:
    """

    @wraps(cls)
    def wrapper(*args, **kwargs):
        return KProducer(*args, **kwargs)

    return wrapper


@mock_producer
def producer_factory(_conf):
    return ConfluentProducer(_conf)


# producer = producer_factory({'bootstrap.servers': 'localhost:9092'})

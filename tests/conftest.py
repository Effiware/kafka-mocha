from pytest import fixture

@fixture
def foo_header() -> tuple:
    return "header_key", "header_value".encode("utf-8")


@fixture(scope="function")
def fresh_kafka():
    from kafka_mocha.kafka_simulator import KafkaSimulator
    return KafkaSimulator()

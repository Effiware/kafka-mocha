import os

from importlib import reload
from pytest import fixture

@fixture
def foo_header() -> tuple:
    return "header_key", "header_value".encode("utf-8")


@fixture(scope="function")
def fresh_kafka():
    """Returns fresh (reloaded) KafkaSimulator singleton instance"""
    import kafka_mocha.kafka_simulator
    reload(kafka_mocha.kafka_simulator)
    return kafka_mocha.kafka_simulator.KafkaSimulator()



@fixture(scope="function")
def fresh_kafka_auto_topic_create_off():
    """Yields fresh (reloaded) KafkaSimulator singleton instance with auto topic create off"""
    old_value = os.environ.get("KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE", "true")
    os.environ["KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE"] = "false"

    import kafka_mocha.kafka_simulator
    reload(kafka_mocha.kafka_simulator)
    yield kafka_mocha.kafka_simulator.KafkaSimulator()
    os.environ["KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE"] = old_value

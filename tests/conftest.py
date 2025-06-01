import os
from importlib import reload
from logging import LogRecord

from pytest import fixture


@fixture
def foo_header() -> tuple:
    return "header_key", "header_value".encode("utf-8")


@fixture(scope="function")
def foo_log_record() -> LogRecord:
    return LogRecord(
        name="foo",
        level=20,
        pathname="foo.py",
        lineno=42,
        msg="foo",
        args=(),
        exc_info=None,
    )


@fixture(scope="module")
def kafka():
    """Returns KafkaSimulator singleton instance."""
    import kafka_mocha.kafka_simulator as km

    kafka = km.KafkaSimulator
    kafka._instance = None
    yield kafka()


@fixture(scope="function")
def fresh_kafka():
    """Yields fresh KafkaSimulator singleton instance."""
    import kafka_mocha.kafka_simulator as km

    kafka = km.KafkaSimulator
    kafka._instance = None
    yield kafka()


@fixture(scope="function")
def fresh_kafka__reloaded():
    """Yields fresh (reloaded) KafkaSimulator singleton instance.

    Should be used at the end of test executions as reloads cause problems.
    """
    import kafka_mocha.kafka_simulator as km

    reload(km)
    kafka = km.KafkaSimulator
    kafka._instance = None
    yield kafka()


@fixture(scope="function")
def fresh_kafka_auto_topic_create_off__reloaded():
    """Yields fresh (reloaded) KafkaSimulator singleton instance with auto topic create off.

    Should be used at the end of test executions as reloads cause problems.
    """
    old_value = os.environ.get("KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE", "true")
    os.environ["KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE"] = "false"

    import kafka_mocha.kafka_simulator as km

    reload(km)
    kafka = km.KafkaSimulator
    kafka._instance = None
    yield kafka()
    os.environ["KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE"] = old_value


@fixture()
def kproducer(kafka):
    """Returns KProducer instance."""
    import kafka_mocha.kproducer as kp

    return kp.KProducer({"bootstrap.servers": "localhost:9092"})


@fixture()
def kconsumer(kafka):
    """Returns KConsumer instance."""
    import kafka_mocha.kconsumer as kc

    return kc.KConsumer({"bootstrap.servers": "localhost:9092", "group.id": "test-group"})

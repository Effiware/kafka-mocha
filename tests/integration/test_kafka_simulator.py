import logging

from kafka_mocha.kafka_simulator import KafkaSimulator

def test_kafka_simulator_bootstrap(caplog):
    caplog.set_level(logging.DEBUG)
    kafka = KafkaSimulator()

    assert kafka is not None
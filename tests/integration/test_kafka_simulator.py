from kafka_mocha.kafka_simulator import KafkaSimulator


def test_kafka_simulator_bootstrap(fresh_kafka):
    assert fresh_kafka is not None


def test_kafka_simulator_getting_topics(fresh_kafka):
    topics = fresh_kafka.get_topics()

    assert len(topics.keys()) == 2
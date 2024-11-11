import json
import os


def test_kafka_simulator_bootstrap(fresh_kafka):
    assert fresh_kafka is not None
    assert fresh_kafka._instance is not None
    assert fresh_kafka is fresh_kafka._instance


def test_kafka_simulator_getting_topics(fresh_kafka):
    env_topics = json.loads(os.environ.get("KAFKA_MOCHA_KSIM_TOPICS", "[]"))
    cluster_metadata = fresh_kafka.get_topics()

    assert len(cluster_metadata.topics.keys()) == len(env_topics) + 2


def test_kafka_simulator_getting_topics_non_existent_auto_off(fresh_kafka_auto_topic_create_off):
    """Test that Kafka Simulator does not create new topic when it does not exist and AUTO_CREATE off"""
    cluster_metadata = fresh_kafka_auto_topic_create_off.get_topics("non-existent")

    assert len(cluster_metadata.topics.keys()) == 0


def test_kafka_simulator_getting_topics_non_existent_auto_on(fresh_kafka):
    """Test that Kafka Simulator creates new topic when it does not exist and AUTO_CREATE on"""
    cluster_metadata = fresh_kafka.get_topics("non-existent")

    assert len(cluster_metadata.topics.keys()) == 1



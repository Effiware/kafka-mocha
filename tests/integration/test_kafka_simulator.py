import json
import os
from inspect import GEN_SUSPENDED, getgeneratorstate

import pytest


@pytest.hookimpl(tryfirst=True)
def test_kafka_simulator_bootstrap(fresh_kafka) -> None:
    """Test that Kafka Simulator is bootstrapped correctly."""
    assert fresh_kafka is not None
    assert fresh_kafka._instance is not None
    assert fresh_kafka is fresh_kafka._instance


@pytest.hookimpl(tryfirst=True)
def test_kafka_simulator_is_singleton(fresh_kafka) -> None:
    """Test that Kafka Simulator is actually a singleton."""
    import kafka_mocha.core.kafka_simulator

    new_kafka = kafka_mocha.core.kafka_simulator.KafkaSimulator()

    assert new_kafka is fresh_kafka
    assert new_kafka._instance is fresh_kafka._instance


@pytest.hookimpl(tryfirst=True)
def test_kafka_simulator_getting_topics(fresh_kafka) -> None:
    """Test that Kafka Simulator gets all topics from environment variable."""
    env_topics = json.loads(os.environ.get("KAFKA_MOCHA_KSIM_TOPICS", "[]"))
    cluster_metadata = fresh_kafka.get_cluster_mdata()

    assert len(cluster_metadata.topics.keys()) == len(env_topics) + 2


@pytest.hookimpl(tryfirst=True)
def test_kafka_simulator_getting_topics_non_existent_auto_on(fresh_kafka) -> None:
    """Test that Kafka Simulator creates new topic when it does not exist and AUTO_CREATE on."""
    cluster_metadata = fresh_kafka.get_cluster_mdata("non-existent")

    assert len(cluster_metadata.topics.keys()) == 1


@pytest.hookimpl(tryfirst=True)
def test_kafka_simulator_producer_handler_is_primed(fresh_kafka) -> None:
    """Test that Kafka Simulator producer handler is primed after initialization."""
    assert getgeneratorstate(fresh_kafka.producers_handler) == GEN_SUSPENDED

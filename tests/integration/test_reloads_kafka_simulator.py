"""
This module uses `__reloaded` fixtures that cause problems when used between "normal" Embedded Kafka instances.
For this reason they are (should) be invoked at the end.
"""

import pytest


@pytest.hookimpl(trylast=True)
def test_kafka_simulator_getting_topics_non_existent_auto_off__reload(fresh_kafka_auto_topic_create_off__reloaded):
    """Test that Kafka Simulator does not create new topic when it does not exist and AUTO_CREATE off"""
    cluster_metadata = fresh_kafka_auto_topic_create_off__reloaded.get_cluster_mdata("non-existent")

    assert len(cluster_metadata.topics.keys()) == 0


@pytest.hookimpl(trylast=True)
def test_kafka_simulator_getting_topics_non_existent_auto_on__reload(fresh_kafka__reloaded):
    """Test that Kafka Simulator creates new topic when it does not exist and AUTO_CREATE on"""
    cluster_metadata = fresh_kafka__reloaded.get_cluster_mdata("non-existent")

    assert len(cluster_metadata.topics.keys()) == 1

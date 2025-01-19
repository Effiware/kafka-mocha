import json
import os
from threading import Lock
from typing import Literal, Optional

from confluent_kafka.admin import BrokerMetadata, ClusterMetadata, PartitionMetadata, TopicMetadata

from kafka_mocha.exceptions import KafkaServerBootstrapException, KafkaSimulatorBootstrapException
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import KRecord, KTopic, PMessage
from kafka_mocha.renderers import render
from kafka_mocha.signals import KSignals

try:
    ONE_ACK_DELAY = os.environ.get("KAFKA_MOCHA_KSIM_ONE_ACK_DELAY", 1)
    ALL_ACK_DELAY = os.environ.get("KAFKA_MOCHA_KSIM_ALL_ACK_DELAY", 3)
    MESSAGE_TIMESTAMP_TYPE = os.environ.get("KAFKA_MOCHA_KSIM_MESSAGE_TIMESTAMP_TYPE", "EventTime")
    AUTO_CREATE_TOPICS_ENABLE = os.environ.get("KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE", "true").lower() == "true"
    TOPICS = json.loads(os.environ.get("KAFKA_MOCHA_KSIM_TOPICS", "[]"))
except KeyError as err:
    raise KafkaSimulatorBootstrapException(f"Missing Kafka Mocha required variable: {err}") from None

logger = get_custom_logger()


class KafkaSimulator:
    _instance = None
    _lock = Lock()
    _is_running = False

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.one_ack_delay = ONE_ACK_DELAY
        self.all_ack_delay = ALL_ACK_DELAY
        self.topics = [KTopic.from_env(topic) for topic in TOPICS]
        self.topics.append(KTopic("_schemas"))  #  Built-in `_schemas` topic
        self.topics.append(KTopic("__consumer_offsets"))  #  Built-in `__consumer_offsets` topic
        logger.info(f"Kafka Simulator initialized")
        logger.debug(f"Registered topics: {self.topics}")

    def _topics_2_cluster_metadata(self, topics: Optional[list[KTopic]] = None) -> ClusterMetadata:
        """Converts KTopics into ClusterMetadata (stubbed)."""

        def _t_metadata_factory(_topic: KTopic) -> TopicMetadata:
            partitions = dict()
            for idx, _ in enumerate(_topic.partitions):
                p_metadata = PartitionMetadata()
                p_metadata.id = idx
                p_metadata.leader = 1
                p_metadata.replicas = [1]
                p_metadata.isrs = [1]
                partitions[idx] = p_metadata

            t_metadata = TopicMetadata()
            t_metadata.topic = _topic.name
            t_metadata.partitions = partitions
            return t_metadata

        _topics = topics if topics is not None else self.topics
        ts_metadata = {topic.name: _t_metadata_factory(topic) for topic in _topics}

        b_metadata = BrokerMetadata()
        b_metadata.id = 1
        b_metadata.host = "127.0.0.1"
        b_metadata.port = 9092

        c_metadata = ClusterMetadata()
        c_metadata.cluster_id = "___KAFKA_SIMULATOR____"
        c_metadata.controller_id = 1
        c_metadata.brokers = b_metadata
        c_metadata.topics = ts_metadata
        c_metadata.orig_broker_name = "localhost:9092/bootstrap"
        return c_metadata

    def get_cluster_mdata(self, topic_name: str = None) -> ClusterMetadata:
        if topic_name is None:
            return self._topics_2_cluster_metadata()

        matching_topics = list(filter(lambda x: x.name == topic_name, self.topics))
        if matching_topics:
            return self._topics_2_cluster_metadata(matching_topics)
        elif AUTO_CREATE_TOPICS_ENABLE:
            self.topics.append(KTopic(topic_name, 1))
            matching_topics = list(filter(lambda x: x.name == topic_name, self.topics))
            return self._topics_2_cluster_metadata(matching_topics)
        else:
            return self._topics_2_cluster_metadata([])

    def handle_producers(self):
        logger.info("Handle producers has been primed")
        last_received_msg_ts = -1.0
        while True:
            received_msgs: list[PMessage] = yield KSignals.SUCCESS  # buffered
            last_received_msg_ts = received_msgs[-1].timestamp if received_msgs else last_received_msg_ts
            for msg in received_msgs:
                _msg_destination_topic = [topic for topic in self.topics if topic.name == msg.topic]
                if not _msg_destination_topic and not AUTO_CREATE_TOPICS_ENABLE:
                    raise KafkaServerBootstrapException(
                        f"Topic {msg.topic} does not exist and "
                        f"KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE set to {AUTO_CREATE_TOPICS_ENABLE} "
                    )
                elif not _msg_destination_topic and AUTO_CREATE_TOPICS_ENABLE:
                    self.topics.append(KTopic(msg.topic, 1))
                    _msg_destination_topic = self.topics
                elif len(_msg_destination_topic) > 1:
                    raise KafkaServerBootstrapException("We have a bug here....")

                _topic = _msg_destination_topic[-1]  # [kpartition][-1] == kpartition
                try:
                    partition = _topic.partitions[msg.partition]
                except IndexError:
                    raise KafkaServerBootstrapException(f"Invalid partition assignment: {msg.partition}")
                else:
                    if msg.pid:
                        _msg_pid_already_appended = msg.pid in [krecord.pid for krecord in partition._heap]
                        if _msg_pid_already_appended:
                            continue
                    last_offset = 1000 + len(partition._heap)
                    k_record = KRecord.from_pmessage(msg, last_offset, MESSAGE_TIMESTAMP_TYPE, last_received_msg_ts)
                    partition.append(k_record)
                    logger.debug(f"Appended message: {k_record}")

    def handle_consumers(self):
        while True:
            yield

    # def run(self):
    #     # handle producers
    #     while True:
    #         try:
    #             self.handle_consumers()
    #         except StopIteration:
    #             print("[KAFKA] Consumers handled")
    #
    #         try:
    #             self.handle_producers()
    #         except StopIteration:
    #             print("[KAFKA] Producers handled")

    def render_records(self, output: Literal["html", "csv"]):
        if output:
            render(output, self.topics)
        else:
            logger.error("No output format has been set. Rendering skipped.")

    def __del__(self):
        logger.debug("Kafka Simulator has been terminated.")

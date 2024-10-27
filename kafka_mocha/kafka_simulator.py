import json
import os

from kafka_mocha.exceptions import KafkaSimulatorBootstrapException, KafkaServerBootstrapException
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import KTopic, KRecord, PMessage
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
    _is_running = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(KafkaSimulator, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
    ):
        self.one_ack_delay = ONE_ACK_DELAY
        self.all_ack_delay = ALL_ACK_DELAY
        self.topics = [KTopic.from_env(topic) for topic in TOPICS]
        logger.info(f"Kafka Simulator initialized")
        logger.debug(f"Registered topics: {self.topics}")

    def get_topics(self) -> dict[str, dict]:
        return {topic.name: {"partition_no": topic.partition_no, "config": topic.config} for topic in self.topics}

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

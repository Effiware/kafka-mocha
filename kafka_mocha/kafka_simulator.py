import json
import os

from kafka_mocha.exceptions import KafkaSimulatorBootstrapException, KafkaServerBootstrapException
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import KTopic, KRecord, PMessage
from kafka_mocha.signals import KSignals

try:
    ONE_ACK_DELAY = os.environ.get("KAFKA_MOCHA_KSIM_ONE_ACK_DELAY", 1)
    ALL_ACK_DELAY = os.environ.get("KAFKA_MOCHA_KSIM_ALL_ACK_DELAY", 3)
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

    def list_topics(self) -> list[KTopic]:
        return self.topics

    def handle_producers(self):
        logger.info("Handle producers has been primed")
        while True:
            received_msgs: list[PMessage] = yield KSignals.SUCCESS  # buffered
            for msg in received_msgs:
                _msg_destination_topic = [topic for topic in self.topics if topic.name == msg.topic]
                if not _msg_destination_topic and not AUTO_CREATE_TOPICS_ENABLE:
                    raise KafkaServerBootstrapException(
                        f"Topic {msg.topic} does not exist and "
                        f"KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE set to {AUTO_CREATE_TOPICS_ENABLE} "
                    )
                elif not _msg_destination_topic and AUTO_CREATE_TOPICS_ENABLE:
                    self.topics.append(KTopic(msg.topic, 1))
                    _msg_destination_topic = [topic for topic in self.topics if topic.name == msg.topic]
                elif len(_msg_destination_topic) > 1:
                    raise KafkaServerBootstrapException("We have a bug here....")

                _topic = _msg_destination_topic[0]
                try:
                    _partition = _topic.partitions[msg.partition]
                except IndexError:
                    raise KafkaServerBootstrapException(f"Invalid partition assignment: {msg.partition}")
                else:
                    if msg.pid:
                        _msg_pid_already_appended = msg.pid in [krecord.pid for krecord in _partition._heap]
                        if _msg_pid_already_appended:
                            continue
                    _last_offset = _partition._heap[-1][7] if len(_partition._heap) > 0 else 0
                    _partition.append(KRecord.from_pmessage(msg, _last_offset))
            logger.info(f"Received messages: {received_msgs}")

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

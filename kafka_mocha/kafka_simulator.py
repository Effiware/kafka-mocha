import json
import os
from collections import defaultdict
from inspect import GEN_SUSPENDED, getgeneratorstate
from threading import Lock
from typing import Any, Literal, NamedTuple, Optional

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import BrokerMetadata, ClusterMetadata, PartitionMetadata, TopicMetadata

from kafka_mocha.exceptions import KafkaSimulatorBootstrapException, KafkaSimulatorProcessingException
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


class ProducerAndState(NamedTuple):
    producer_id: int
    is_ongoing: bool = False


class KafkaSimulator:
    """Kafka Simulator (singleton) class that acts as a mock Kafka Broker.

    It fully replicates the Kafka Broker's behavior and provides a way to simulate Kafka's behavior in a controlled
    environment. It is a singleton class that can be accessed from anywhere in the codebase.
    As a rule of thumb, it shouldn't be instantiated or used directly. Instead, it's internally used by the KProducer
    and KConsumer classes and can be manipulated by:
    - environment variables prefixed with `KAFKA_MOCHA_KSIM` (e.g. KAFKA_MOCHA_KSIM_ONE_ACK_DELAY, see README.md)
    - wrapper function parameters (e.g. mock_producer, mock_consumer, either as a decorator or context manager)
    """

    TRANSACT_TOPIC = "__transaction_state"
    TRANSACT_TOPIC_PARTITION_NO = 50
    _instance = None
    _lock = Lock()
    _is_running = False

    producers_handler = None

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.one_ack_delay = ONE_ACK_DELAY
        self.all_ack_delay = ALL_ACK_DELAY
        self.topics: list[KTopic] = [KTopic.from_env(topic) for topic in TOPICS]
        self.topics.append(KTopic("_schemas"))  # Built-in `_schemas` topic
        self.topics.append(KTopic("__consumer_offsets"))  # Built-in `__consumer_offsets` topic
        self._registered_transact_ids: dict[str, list[ProducerAndState]] = defaultdict(list)  # Epoch is list length

        self.producers_handler = self.handle_producers()
        self.producers_handler.send(KSignals.INIT.value)

        logger.info("Kafka Simulator initialized, id: %s", id(self))
        logger.debug("Registered topics: %s", self.topics)

    def _topics_2_cluster_metadata(self, topics: Optional[list[KTopic]] = None) -> ClusterMetadata:
        """Converts KTopics into ClusterMetadata (stubbed)."""

        def _t_metadata_factory(_topic: KTopic) -> TopicMetadata:
            """Converts KTopic into TopicMetadata."""
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
        """Returns ClusterMetadata object from Kafka Simulator (acts as if it was real Kafka Broker)."""
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

    def register_producer_transaction_id(self, producer_id: int, transactional_id: str) -> None:
        """Registers transactional id for producer. Also, prepares transaction coordinator and needed infrastructure."""
        topics = list(filter(lambda x: x.name == self.TRANSACT_TOPIC, self.topics))
        if not topics:
            # Register transaction log topic
            topic = KTopic(self.TRANSACT_TOPIC, self.TRANSACT_TOPIC_PARTITION_NO, config={"cleanup.policy": "compact"})
            self.topics.append(topic)
        self._registered_transact_ids[transactional_id].append(ProducerAndState(producer_id))

    def transaction_coordinator(
        self,
        state: Literal["init", "begin", "commit", "abort"],
        producer_id: int,
        transactional_id: str,
        dry_run: bool = False,
    ) -> None:
        """
        Transaction coordinator that handles transaction(s) flow. Transaction state checks are split between
        transaction_coordinator and Kproducer. Here, only initializations and state transitions are handled.
        """
        handler = self.producers_handler
        if getgeneratorstate(handler) != GEN_SUSPENDED:
            raise KafkaSimulatorProcessingException(
                "Potential bug: producers handler should be suspended at this point... %s", getgeneratorstate(handler)
            )

        producer_epoch = len(self._registered_transact_ids[transactional_id]) - 1
        msg_partition = abs(hash(transactional_id)) % self.TRANSACT_TOPIC_PARTITION_NO
        msg_key = {"transactionalId": transactional_id, "version": 0}
        msg_value = {
            "transactionalId": transactional_id,
            "producerId": producer_id,
            "lastProducerId": -1,
            "producerEpoch": producer_epoch,
            "lastProducerEpoch": -1,
            "txnTimeoutMs": 60000,
            "state": "",
            "topicPartitions": [],
            "txnStartTimestamp": -1,
            "txnLastUpdateTimestamp": -1,
        }

        match state:
            case "init":
                self.register_producer_transaction_id(producer_id, transactional_id)
                msg_value["producerEpoch"] = len(self._registered_transact_ids[transactional_id]) - 1
                msg_value["state"] = "Empty"
                msgs = [PMessage(self.TRANSACT_TOPIC, msg_partition, str(msg_key).encode(), str(msg_value).encode())]

            case "begin":
                if producer_id not in map(lambda x: x[0], self._registered_transact_ids[transactional_id]):
                    raise KafkaException(KafkaError(KafkaError._STATE, "Operation not valid in state Init", fatal=True))

                transaction_for_producer = list(
                    filter(lambda x: x[0] == producer_id, self._registered_transact_ids[transactional_id])
                )
                if len(transaction_for_producer) > 1:
                    raise KafkaSimulatorProcessingException("What now?")
                elif transaction_for_producer[-1][1]:
                    raise KafkaException(
                        KafkaError(KafkaError._STATE, "Operation not valid in state Ready", fatal=True)
                    )

                msg_value["state"] = "Ongoing"
                msgs = [PMessage(self.TRANSACT_TOPIC, msg_partition, str(msg_key).encode(), str(msg_value).encode())]
                if not dry_run:
                    # Set it state to ongoing
                    for idx, _id in enumerate(self._registered_transact_ids[transactional_id]):
                        if _id[0] == producer_id:
                            self._registered_transact_ids[transactional_id][idx] = ProducerAndState(producer_id, True)

            case "commit":
                if producer_id not in map(lambda x: x[0], self._registered_transact_ids[transactional_id]):
                    raise KafkaException(KafkaError(KafkaError._STATE, "Operation not valid in state Init", fatal=True))

                transaction_for_producer = list(
                    filter(lambda x: x[0] == producer_id, self._registered_transact_ids[transactional_id])
                )
                if producer_id != transaction_for_producer[-1][0]:
                    kafka_error = KafkaError(
                        KafkaError._FENCED,  # error code -144
                        "Failed to end transaction: Local: This instance has been fenced by a newer instance",
                        fatal=True,
                    )
                    raise KafkaException(kafka_error)
                elif not transaction_for_producer[-1][1]:
                    raise KafkaException(
                        KafkaError(KafkaError._STATE, "Operation not valid in state Ready", fatal=True)
                    )

                msg_value["state"] = "PrepareCommit"
                msgs = [PMessage(self.TRANSACT_TOPIC, msg_partition, str(msg_key).encode(), str(msg_value).encode())]
                msg_value["state"] = "CompleteCommit"
                msgs.append(
                    PMessage(self.TRANSACT_TOPIC, msg_partition, str(msg_key).encode(), str(msg_value).encode())
                )
                if not dry_run:
                    # Reset state
                    for idx, _id in enumerate(self._registered_transact_ids[transactional_id]):
                        if _id[0] == producer_id:
                            self._registered_transact_ids[transactional_id][idx] = ProducerAndState(producer_id, False)

            case "abort":
                if producer_id not in map(lambda x: x[0], self._registered_transact_ids[transactional_id]):
                    raise KafkaException(KafkaError(KafkaError._STATE, "Operation not valid in state Init", fatal=True))

                msg_value["state"] = "Abort"
                msgs = [PMessage(self.TRANSACT_TOPIC, msg_partition, str(msg_key).encode(), str(msg_value).encode())]
                if not dry_run:
                    # Reset state
                    for idx, _id in enumerate(self._registered_transact_ids[transactional_id]):
                        if _id[0] == producer_id:
                            self._registered_transact_ids[transactional_id][idx] = ProducerAndState(producer_id, False)

            case _:
                raise ValueError(f"Invalid transaction state: {state}")

        if not dry_run:
            handler.send(msgs)

    def handle_producers(self):
        """A separate generator function that yields a signal to the caller. Handles incoming messages from producers.

        :note: Separate/common event-loop-like for handling producers/consumers are being tested.
        """
        logger.info("Handle producers has been primed")
        last_received_msg_ts = -1.0
        while True:
            received_msgs: list[PMessage] = yield KSignals.SUCCESS  # buffered
            last_received_msg_ts = received_msgs[-1].timestamp if received_msgs else last_received_msg_ts
            for msg in received_msgs:
                _msg_destination_topic = [topic for topic in self.topics if topic.name == msg.topic]
                if not _msg_destination_topic and not AUTO_CREATE_TOPICS_ENABLE:
                    raise KafkaSimulatorProcessingException(
                        f"Topic {msg.topic} does not exist and "
                        f"KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE set to {AUTO_CREATE_TOPICS_ENABLE} "
                    )
                elif not _msg_destination_topic and AUTO_CREATE_TOPICS_ENABLE:
                    self.topics.append(KTopic(msg.topic, 1))
                    _msg_destination_topic = self.topics
                elif len(_msg_destination_topic) > 1:
                    raise KafkaSimulatorProcessingException("We have a bug here....")

                _topic = _msg_destination_topic[-1]  # [kpartition][-1] == kpartition
                try:
                    partition = _topic.partitions[msg.partition]
                except IndexError:
                    raise KafkaSimulatorProcessingException(f"Invalid partition assignment: {msg.partition}")
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
        """A separate generator function that yields a signal to the caller. Handles delivering messages to consumer.

        :note: Separate/common event-loop-like for handling producers/consumers are being tested.
        """
        while True:
            yield NotImplemented

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

    def render_records(self, output: dict[str, Any]):
        """Renders Kafka records in the specified format."""
        _format = output.pop("format", None)
        if _format is not None:
            render(_format, self.topics, **output)
        else:
            logger.error("No output format has been set. Rendering skipped.")

    def __del__(self):
        logger.debug("Kafka Simulator has been terminated.")

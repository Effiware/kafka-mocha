import json
import os
from collections import defaultdict
from inspect import GEN_SUSPENDED, getgeneratorstate
from threading import Lock
from typing import Any, Literal, NamedTuple, Optional

import confluent_kafka
from confluent_kafka.admin import (
    BrokerMetadata,
    ClusterMetadata,
    PartitionMetadata,
    TopicMetadata,
)

from kafka_mocha.exceptions import (
    KafkaSimulatorBootstrapException,
    KafkaSimulatorProcessingException,
)
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models.kmodels import KConsumerGroup, KMessage, KTopic
from kafka_mocha.models.signals import KSignals
from kafka_mocha.renderers import render

try:
    ONE_ACK_DELAY = os.environ.get("KAFKA_MOCHA_KSIM_ONE_ACK_DELAY", 1)
    ALL_ACK_DELAY = os.environ.get("KAFKA_MOCHA_KSIM_ALL_ACK_DELAY", 3)
    MESSAGE_TIMESTAMP_TYPE = os.environ.get(
        "KAFKA_MOCHA_KSIM_MESSAGE_TIMESTAMP_TYPE", confluent_kafka.TIMESTAMP_CREATE_TIME
    )
    AUTO_CREATE_TOPICS_ENABLE = (
        os.environ.get("KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE", "true").lower()
        == "true"
    )
    TOPICS = json.loads(os.environ.get("KAFKA_MOCHA_KSIM_TOPICS", "[]"))
except KeyError as err:
    raise KafkaSimulatorBootstrapException(
        f"Missing Kafka Mocha required variable: {err}"
    ) from None

SYSTEM_TOPICS = ["_schemas", "__consumer_offsets"]
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
    consumers_handler = None

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._is_running:
            return
        # self.one_ack_delay = ONE_ACK_DELAY
        # self.all_ack_delay = ALL_ACK_DELAY
        self.topics: list[KTopic] = [KTopic.from_env(topic) for topic in TOPICS]
        for sys_topic in SYSTEM_TOPICS:
            self.topics.append(KTopic(sys_topic))
        self._registered_transact_ids: dict[str, list[ProducerAndState]] = defaultdict(
            list
        )  # Epoch is list length

        # Consumer group management
        self._consumer_groups: dict[str, KConsumerGroup] = {}
        self._consumer_2_group: dict[int, str] = {}  # consumer_id -> group_id mapping

        # Transactional offset commits - keyed by (producer_id, transactional_id)
        self._pending_transactional_offsets: dict[tuple[int, str], list[KMessage]] = (
            defaultdict(list)
        )

        # Start handlers
        self.producers_handler = self.handle_producers()
        self.producers_handler.send(KSignals.INIT.value)

        self.consumers_handler = self.handle_consumers()
        self.consumers_handler.send(KSignals.INIT.value)

        self._is_running = True
        logger.info("Kafka Simulator initialized, id: %s", id(self))
        logger.debug("Registered topics: %s", self.topics)

    def reset(self):
        self._is_running = False
        self.__init__()

    def _topics_2_cluster_metadata(
        self, topics: Optional[list[KTopic]] = None
    ) -> ClusterMetadata:
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

    def register_producer_transaction_id(
        self, producer_id: int, transactional_id: str
    ) -> None:
        """Registers transactional id for producer. Also, prepares transaction coordinator and needed infrastructure."""
        topics = list(filter(lambda x: x.name == self.TRANSACT_TOPIC, self.topics))
        if not topics:
            # Register transaction log topic
            topic = KTopic(
                self.TRANSACT_TOPIC,
                self.TRANSACT_TOPIC_PARTITION_NO,
                config={"cleanup.policy": "compact"},
            )
            self.topics.append(topic)
        self._registered_transact_ids[transactional_id].append(
            ProducerAndState(producer_id)
        )

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
                "Potential bug: producers handler should be suspended at this point... %s",
                getgeneratorstate(handler),
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
                msg_value["producerEpoch"] = (
                    len(self._registered_transact_ids[transactional_id]) - 1
                )
                msg_value["state"] = "Empty"
                msgs = [
                    KMessage(
                        self.TRANSACT_TOPIC,
                        msg_partition,
                        str(msg_key).encode(),
                        str(msg_value).encode(),
                    )
                ]

            case "begin":
                if producer_id not in map(
                    lambda x: x[0], self._registered_transact_ids[transactional_id]
                ):
                    raise confluent_kafka.KafkaException(
                        confluent_kafka.KafkaError(
                            confluent_kafka.KafkaError._STATE,
                            "Operation not valid in state Init",
                            fatal=True,
                        )
                    )
                transaction_for_producer = list(
                    filter(
                        lambda x: x[0] == producer_id,
                        self._registered_transact_ids[transactional_id],
                    )
                )
                if len(transaction_for_producer) > 1:
                    raise KafkaSimulatorProcessingException("What now?")
                elif transaction_for_producer[-1][1]:
                    raise confluent_kafka.KafkaException(
                        confluent_kafka.KafkaError(
                            confluent_kafka.KafkaError._STATE,
                            "Operation not valid in state Ready",
                            fatal=True,
                        )
                    )
                msg_value["state"] = "Ongoing"
                msgs = [
                    KMessage(
                        self.TRANSACT_TOPIC,
                        msg_partition,
                        str(msg_key).encode(),
                        str(msg_value).encode(),
                    )
                ]
                if not dry_run:
                    # set it state to ongoing
                    for idx, _id in enumerate(
                        self._registered_transact_ids[transactional_id]
                    ):
                        if _id[0] == producer_id:
                            self._registered_transact_ids[transactional_id][idx] = (
                                ProducerAndState(producer_id, True)
                            )

            case "commit":
                if producer_id not in map(
                    lambda x: x[0], self._registered_transact_ids[transactional_id]
                ):
                    raise confluent_kafka.KafkaException(
                        confluent_kafka.KafkaError(
                            confluent_kafka.KafkaError._STATE,
                            "Operation not valid in state Init",
                            fatal=True,
                        )
                    )
                transaction_for_producer = list(
                    filter(
                        lambda x: x[0] == producer_id,
                        self._registered_transact_ids[transactional_id],
                    )
                )
                if producer_id != transaction_for_producer[-1][0]:
                    kafka_error = confluent_kafka.KafkaError(
                        confluent_kafka.KafkaError._FENCED,  # error code -144
                        "Failed to end transaction: Local: This instance has been fenced by a newer instance",
                        fatal=True,
                    )
                    raise confluent_kafka.KafkaException(kafka_error)
                elif not transaction_for_producer[-1][1]:
                    raise confluent_kafka.KafkaException(
                        confluent_kafka.KafkaError(
                            confluent_kafka.KafkaError._STATE,
                            "Operation not valid in state Ready",
                            fatal=True,
                        )
                    )
                msg_value["state"] = "PrepareCommit"
                msgs = [
                    KMessage(
                        self.TRANSACT_TOPIC,
                        msg_partition,
                        str(msg_key).encode(),
                        str(msg_value).encode(),
                    )
                ]
                msg_value["state"] = "CompleteCommit"
                msgs.append(
                    KMessage(
                        self.TRANSACT_TOPIC,
                        msg_partition,
                        str(msg_key).encode(),
                        str(msg_value).encode(),
                    )
                )
                if not dry_run:
                    # Commit pending transactional offset commits
                    self._commit_pending_transactional_offsets(
                        producer_id, transactional_id
                    )

                    # Reset state
                    for idx, _id in enumerate(
                        self._registered_transact_ids[transactional_id]
                    ):
                        if _id[0] == producer_id:
                            self._registered_transact_ids[transactional_id][idx] = (
                                ProducerAndState(producer_id, False)
                            )

            case "abort":
                if producer_id not in map(
                    lambda x: x[0], self._registered_transact_ids[transactional_id]
                ):
                    raise confluent_kafka.KafkaException(
                        confluent_kafka.KafkaError(
                            confluent_kafka.KafkaError._STATE,
                            "Operation not valid in state Init",
                            fatal=True,
                        )
                    )
                msg_value["state"] = "Abort"
                msgs = [
                    KMessage(
                        self.TRANSACT_TOPIC,
                        msg_partition,
                        str(msg_key).encode(),
                        str(msg_value).encode(),
                    )
                ]
                if not dry_run:
                    # Abort pending transactional offset commits
                    self._abort_pending_transactional_offsets(producer_id, transactional_id)

                    # Reset state
                    for idx, _id in enumerate(
                        self._registered_transact_ids[transactional_id]
                    ):
                        if _id[0] == producer_id:
                            self._registered_transact_ids[transactional_id][idx] = (
                                ProducerAndState(producer_id, False)
                            )

            case _:
                raise ValueError(f"Invalid transaction {state=}")

        if not dry_run:
            handler.send(msgs)

    def handle_producers(self):
        """A separate generator function that yields a signal to the caller. Handles incoming messages from producers.

        :note: Separate/common event-loop-like for handling producers/consumers are being tested.
        """
        logger.info("Handle producers has been primed")
        last_received_msg_ts = -1
        while True:
            received_msgs: list[KMessage] = yield KSignals.SUCCESS  # buffered
            last_received_msg_ts = (
                received_msgs[-1].timestamp()[1]
                if received_msgs
                else last_received_msg_ts
            )
            for msg in received_msgs:
                _msg_destination_topic = [
                    topic for topic in self.topics if topic.name == msg.topic()
                ]
                if not _msg_destination_topic and not AUTO_CREATE_TOPICS_ENABLE:
                    raise KafkaSimulatorProcessingException(
                        f"Topic {msg.topic()} does not exist and "
                        f"KAFKA_MOCHA_KSIM_AUTO_CREATE_TOPICS_ENABLE set to {AUTO_CREATE_TOPICS_ENABLE} "
                    )
                elif not _msg_destination_topic and AUTO_CREATE_TOPICS_ENABLE:
                    self.topics.append(KTopic(msg.topic(), 1))
                    _msg_destination_topic = self.topics
                elif len(_msg_destination_topic) > 1:
                    raise KafkaSimulatorProcessingException("We have a bug here....")

                _topic = _msg_destination_topic[-1]
                try:
                    partition = _topic.partitions[msg.partition()]
                except IndexError:
                    raise KafkaSimulatorProcessingException(
                        f"Invalid partition assignment: {msg.partition()}"
                    )
                else:
                    if msg._pid:
                        _msg_pid_already_appended = msg._pid in [
                            krecord._pid for krecord in partition._heap
                        ]
                        if _msg_pid_already_appended:
                            continue
                    msg.set_offset(1000 + len(partition))
                    msg.set_timestamp(last_received_msg_ts, MESSAGE_TIMESTAMP_TYPE)
                    partition.append(msg)
                    logger.debug("Appended message: %s", msg)

                    # Handle offset commits to update consumer group state
                    if msg.topic() == "__consumer_offsets" and not msg._marker:
                        if msg._pid and self._is_transactional_producer(msg._pid):
                            # This is a transactional offset commit - store it pending
                            self._store_pending_transactional_offset(msg)
                        else:
                            # Regular offset commit - process immediately
                            self._process_offset_commit(msg)

    def handle_consumers(self):
        """A separate generator function that yields a signal to the caller. Handles delivering messages to consumer.

        :note: Separate/common event-loop-like for handling producers/consumers are being tested.
        """
        logger.info("Handle consumers has been primed")
        result = KSignals.SUCCESS
        while True:
            request = yield result
            if isinstance(request, tuple) and len(request) == 3:
                # Handle a poll request: (consumer_id, topic_partitions, max_records)
                consumer_id, topic_partitions, max_records = request

                # Get all messages for the requested partitions
                messages = []
                for tp in topic_partitions:
                    topic = next((t for t in self.topics if t.name == tp.topic), None)
                    if topic is None or tp.partition >= len(topic.partitions):
                        continue

                    partition = topic.partitions[tp.partition]
                    messages += partition.get_by_offset(tp.offset, max_records)

                logger.debug(
                    "Consumer %d polling, found %d messages", consumer_id, len(messages)
                )
                result = messages

            elif isinstance(request, confluent_kafka.TopicPartition):
                # Handle a seek request
                topic_name = request.topic
                partition_id = request.partition
                offset = request.offset

                # Find the topic
                topic = next((t for t in self.topics if t.name == topic_name), None)
                if topic is None:
                    logger.warning("Seek request for unknown topic: %s", topic_name)
                    result = KSignals.SUCCESS
                    continue

                # Process the request
                logger.warning(
                    "Consumer seeking to offset %d for %s[%d]",
                    offset,
                    topic_name,
                    partition_id,
                )
                result = KSignals.SUCCESS

            else:
                raise KafkaSimulatorProcessingException(
                    f"Unknown request type in consumer handler: {type(request)}"
                )

    def register_consumer(
        self, consumer_id: int, group_id: str, topics: list[str]
    ) -> None:
        """
        Register a consumer with a consumer group.

        :todo: Add regex support for topic names
        """
        logger.debug(
            "Registering consumer %d with group %s, topics: %s",
            consumer_id,
            group_id,
            topics,
        )

        # Create the consumer group if it doesn't exist
        if group_id not in self._consumer_groups:
            self._consumer_groups[group_id] = KConsumerGroup(group_id)

        # Add or update the consumer in the group
        self._consumer_groups[group_id].add_member(consumer_id, topics)
        self._consumer_2_group[consumer_id] = group_id

        # Trigger a rebalance for the group
        self._rebalance_and_notify(group_id)

    def unregister_consumer(self, consumer_id: int) -> None:
        """Unregister a consumer from its consumer group."""
        if consumer_id in self._consumer_2_group:
            group_id = self._consumer_2_group[consumer_id]
            logger.debug(
                "Unregistering consumer %d from group %s", consumer_id, group_id
            )

            # Remove the consumer from the group
            if group_id in self._consumer_groups:
                self._consumer_groups[group_id].remove_member(consumer_id)

                # Trigger a rebalance for the group if there are still members
                if self._consumer_groups[group_id].members:
                    self._rebalance_and_notify(group_id)
            else:
                logger.warning(
                    "Consumer group %s not found for consumer %d", group_id, consumer_id
                )

            # Remove the mapping
            del self._consumer_2_group[consumer_id]

    def _rebalance_and_notify(self, group_id: str) -> None:
        """
        Rebalance a consumer group and notify consumers of their new assignments.
        This method handles the full rebalancing process, including:
        1. Computing new assignments
        2. Revoking old assignments
        3. Assigning new partitions
        """
        if group_id not in self._consumer_groups:
            logger.warning("Consumer group %s not found for rebalance", group_id)
            return

        consumer_group = self._consumer_groups[group_id]
        if not consumer_group.members:
            return

        logger.debug("Running full rebalance for consumer group %s", group_id)
        # Get the old assignments for each consumer
        old_assignments = {}
        for consumer_id in consumer_group.members:
            old_assignments[consumer_id] = consumer_group.get_member_assignment(
                consumer_id
            )

        # Compute new assignments
        new_assignments = consumer_group.rebalance(self.topics)

        # For each consumer, determine what partitions were revoked and what was assigned
        for consumer_id in consumer_group.members:
            old_tps = old_assignments.get(consumer_id, [])
            new_tps = new_assignments.get(consumer_id, [])

            # Identify revoked partitions
            revoked_tps = [
                tp
                for tp in old_tps
                if not any(
                    ntp.topic == tp.topic and ntp.partition == tp.partition
                    for ntp in new_tps
                )
            ]

            # Identify assigned partitions
            assigned_tps = [
                tp
                for tp in new_tps
                if not any(
                    otp.topic == tp.topic and otp.partition == tp.partition
                    for otp in old_tps
                )
            ]

            logger.debug(
                "Consumer %d: revoked=%s, assigned=%s",
                consumer_id,
                revoked_tps,
                assigned_tps,
            )
            # The actual notification of consumers is done through the KConsumer.subscribe method
            # which will query for its assignment

    def assign_partitions(
        self, consumer_id: int, partitions: list[confluent_kafka.TopicPartition]
    ) -> None:
        """Manually assign partitions to a consumer (outside of consumer groups)."""
        # For manual partition assignment, we don't involve consumer groups
        logger.debug(
            "Manually assigning partitions to consumer %d: %s", consumer_id, partitions
        )

    def get_committed_offsets(
        self, consumer_id: int, partitions: list[confluent_kafka.TopicPartition]
    ) -> list[confluent_kafka.TopicPartition]:
        """Get committed offsets for a consumer."""
        result = []

        if consumer_id in self._consumer_2_group:
            group_id = self._consumer_2_group[consumer_id]
            logger.debug(
                "Getting committed offsets for consumer %d in group %s",
                consumer_id,
                group_id,
            )

            if group_id in self._consumer_groups:
                for tp in partitions:
                    offset = self._consumer_groups[group_id].get_offset(
                        tp.topic, tp.partition
                    )
                    result.append(
                        confluent_kafka.TopicPartition(tp.topic, tp.partition, offset)
                    )

        return result

    def _rebalance_group(
        self, group_id: str
    ) -> dict[int, list[confluent_kafka.TopicPartition]]:
        """Rebalance a consumer group and return the new assignments."""
        if group_id not in self._consumer_groups:
            return {}

        logger.debug("Rebalancing consumer group %s", group_id)
        return self._consumer_groups[group_id].rebalance(self.topics)

    def get_member_assignment(
        self, consumer_id: int
    ) -> list[confluent_kafka.TopicPartition]:
        """Get the current assignment for a consumer."""
        if consumer_id in self._consumer_2_group:
            group_id = self._consumer_2_group[consumer_id]
            if group_id in self._consumer_groups:
                return self._consumer_groups[group_id].get_member_assignment(
                    consumer_id
                )
        return []

    def render_records(self, output: dict[str, Any]):
        """Renders Kafka records in the specified format."""
        _format = output.pop("format", None)
        if _format is not None:
            render(_format, self.topics, **output)
        else:
            logger.error("No output format has been set. Rendering skipped.")

    def _process_offset_commit(self, message: KMessage) -> None:
        """Process offset commit message and update consumer group state."""
        try:
            # Parse the offset commit message
            key = (
                message.key().decode()
                if isinstance(message.key(), bytes)
                else message.key()
            )
            value = (
                message.value(None).decode()
                if isinstance(message.value(None), bytes)
                else message.value(None)
            )

            # Expected format: "group_id:topic:partition"
            group_id, topic, partition_str = key.split(":", 2)
            partition = int(partition_str)
            offset = int(value)

            # Update consumer group offsets
            if group_id in self._consumer_groups:
                consumer_group = self._consumer_groups[group_id]
                if topic not in consumer_group.offsets:
                    consumer_group.offsets[topic] = {}

                consumer_group.offsets[topic][partition] = offset
                logger.debug(
                    "Updated offset for group %s, topic %s, partition %d to %d",
                    group_id,
                    topic,
                    partition,
                    offset,
                )
            else:
                logger.debug("Consumer group %s not found for offset commit", group_id)

        except (ValueError, AttributeError) as e:
            logger.warning("Failed to process offset commit message: %s", e)

    def _is_transactional_producer(self, producer_id: int) -> bool:
        """Check if a producer ID belongs to a transactional producer."""
        for transactional_id, producers in self._registered_transact_ids.items():
            if any(p.producer_id == producer_id for p in producers):
                return True
        return False

    def _get_transactional_id_for_producer(self, producer_id: int) -> Optional[str]:
        """Get the transactional ID for a given producer ID."""
        for transactional_id, producers in self._registered_transact_ids.items():
            if any(p.producer_id == producer_id for p in producers):
                return transactional_id
        return None

    def _store_pending_transactional_offset(self, message: KMessage) -> None:
        """Store a transactional offset commit message in pending state."""
        producer_id = message._pid
        transactional_id = self._get_transactional_id_for_producer(producer_id)

        if transactional_id:
            key = (producer_id, transactional_id)
            self._pending_transactional_offsets[key].append(message)
            logger.debug(
                "Stored pending transactional offset commit for producer %d, transaction %s",
                producer_id,
                transactional_id,
            )

    def _commit_pending_transactional_offsets(
        self, producer_id: int, transactional_id: str
    ) -> None:
        """Commit all pending transactional offset commits for a producer."""
        key = (producer_id, transactional_id)
        pending_offsets = self._pending_transactional_offsets.get(key, [])

        logger.debug(
            "Committing %d pending transactional offset commits for producer %d, transaction %s",
            len(pending_offsets),
            producer_id,
            transactional_id,
        )

        # Process all pending offset commits
        for message in pending_offsets:
            self._process_offset_commit(message)

        # Clear the pending offsets
        if key in self._pending_transactional_offsets:
            del self._pending_transactional_offsets[key]

    def _abort_pending_transactional_offsets(
        self, producer_id: int, transactional_id: str
    ) -> None:
        """Abort (discard) all pending transactional offset commits for a producer."""
        key = (producer_id, transactional_id)
        pending_count = len(self._pending_transactional_offsets.get(key, []))

        logger.debug(
            "Aborting %d pending transactional offset commits for producer %d, transaction %s",
            pending_count,
            producer_id,
            transactional_id,
        )

        # Clear the pending offsets without processing them
        if key in self._pending_transactional_offsets:
            del self._pending_transactional_offsets[key]

    def __del__(self):
        logger.debug("Kafka Simulator has been terminated.")

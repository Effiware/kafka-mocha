import json
import signal
from inspect import GEN_SUSPENDED, getgeneratorstate
from time import sleep, time
from typing import Any, Callable, Literal, Optional

import confluent_kafka
import confluent_kafka.schema_registry
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.schema_registry.json_schema import JSONSerializer
from confluent_kafka.serialization import IntegerSerializer, MessageField, SerializationContext, StringSerializer

from kafka_mocha.core.buffer_handler import buffer_handler
from kafka_mocha.core.kafka_simulator import KafkaSimulator
from kafka_mocha.core.ticking_thread import TickingThread
from kafka_mocha.exceptions import KafkaClientBootstrapException, KConsumerMaxRetryException, KConsumerTimeoutException
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models.kmodels import KMessage
from kafka_mocha.models.ktypes import InputFormat, LogLevelType
from kafka_mocha.models.signals import KSignals, Tick
from kafka_mocha.schema_registry import MockSchemaRegistryClient
from kafka_mocha.schema_registry.exceptions import SchemaRegistryError
from kafka_mocha.utils import validate_config


def _get_subject_name_strategy_call(
    subject_name_strategy: Literal["topic", "topic_record", "record"] = "topic",
) -> Callable:
    """
    Get the subject name for the given topic and field type using the provided subject name strategy.
    """
    if subject_name_strategy == "topic_record":
        return confluent_kafka.schema_registry.topic_record_subject_name_strategy
    elif subject_name_strategy == "record":
        return confluent_kafka.schema_registry.record_subject_name_strategy
    else:
        return confluent_kafka.schema_registry.topic_subject_name_strategy


class KConsumer:
    """
    Confluent Kafka Consumer mockup. It is used to simulate and fully imitate Kafka Consumer behaviour.
    It is implemented to retrieve messages from Kafka Simulator and can be safely used in integration
    tests or as an emulator for Kafka Consumer.
    """

    def __init__(
        self,
        config: dict[str, Any],
        inputs: Optional[list[InputFormat]] = None,
        loglevel: LogLevelType = "WARNING",
    ):
        validate_config("consumer", config)
        self.config = config
        self._group_id = config["group.id"]
        self.logger = get_custom_logger(loglevel)

        # Consumer state
        self._subscription: list[str] = []
        self._assignment: list[confluent_kafka.TopicPartition] = []
        self._member_id = f"mock-consumer-{id(self)}"
        self._paused_partitions: list[confluent_kafka.TopicPartition] = []
        self._positions: dict[str, dict[int, int]] = {}  # topic -> partition -> offset

        # Callbacks
        self._on_assign: Optional[Callable] = None
        self._on_revoke: Optional[Callable] = None
        self._on_lost: Optional[Callable] = None

        # Config settings
        auto_offset_reset = config.get("auto.offset.reset", "latest")
        self._auto_offset_reset = auto_offset_reset
        self._enable_auto_commit = config.get("enable.auto.commit", True)
        self._auto_commit_interval_ms = config.get("auto.commit.interval.ms", 5000)
        self._enable_auto_offset_store = config.get("enable.auto.offset.store", True)
        self._max_retry_count = config.get("retries", 6)
        self._retry_backoff = config.get("retry.backoff.ms", 10) / 1000  # in seconds

        # Connect to Schema Registry if load of serialized inputs is requested
        self._schema_registry = None

        # Connect to Kafka simulator, buffer handler and load inputs if provided
        self._kafka_simulator = KafkaSimulator()
        self._buffer = []
        self._buffer_handler = buffer_handler(
            f"KConsumer({id(self)})",
            self._buffer,
            10000,
            self._auto_commit_interval_ms if self._enable_auto_commit else 10000,
        )
        self._buffer_handler.send(KSignals.INIT.value)
        if inputs:
            self._inputs_upload(inputs)
        if self._enable_auto_commit:
            self._ticking_thread = TickingThread(
                f"KConsumer({id(self)})", self._buffer_handler, self._auto_commit_interval_ms // 2
            )
            self._ticking_thread.daemon = True  # TODO 34: Workaround for #34 bug/34-tickingthread-never-joins
            self._ticking_thread.start()

        self.logger.info("KConsumer initialized, id: %s, group: %s", id(self), self._group_id)

    def _inputs_upload(self, inputs: list[InputFormat]) -> None:
        """Upload input data to the Kafka simulator."""
        for _input in inputs:
            if _input.get("source") is None or _input.get("topic") is None:
                raise KafkaClientBootstrapException("Input format must contain 'source' and 'topic' keys")

            with open(_input["source"], "r") as file:
                messages: list[dict] = json.loads(file.read())
                for message in messages:
                    topic = _input["topic"]
                    sns = _input.get("subject_name_strategy")

                    key_field = message.get("key", None)
                    key = key_field["payload"] if key_field else None
                    value_field = message.get("value", None)
                    value = value_field["payload"] if value_field else None
                    headers = message.get("headers", None)
                    
                    if _input.get("serialize", False):
                        if isinstance(key, dict):
                            if key_field and key_field.get("subject"):
                                key = self._input_serialize(key_field, "KEY", topic, sns)
                            else:
                                key = StringSerializer()(json.dumps(key))
                        elif isinstance(key, int):
                            key = IntegerSerializer()(str(key))
                        else:
                            key = StringSerializer()(key)

                        if isinstance(value, dict):
                            if value_field and value_field.get("subject"):
                                value = self._input_serialize(value_field, "VALUE", topic, sns)
                            else:
                                value = StringSerializer()(json.dumps(value))
                        elif isinstance(value, int):
                            value = IntegerSerializer()(str(value))
                        else:
                            value = StringSerializer()(value)
                    else:
                        key = json.dumps(key) if isinstance(key, dict) else key
                        value = json.dumps(value) if isinstance(value, dict) else value

                    self._buffer_handler.send(KMessage(topic, -1, key, value, headers))

                self._tick_buffer()

    def _input_serialize(
        self, field: dict[str, str], ftype: Literal["KEY", "VALUE"], topic: str, subject_name_strategy: Optional[str]
    ) -> bytes:
        """Serialize input data based on the input format. Get schema from the mock schema registry."""
        if self._schema_registry is None:
            self._schema_registry = MockSchemaRegistryClient({"url": "http://localhost:8081"})

        try:
            reg_schema = self._schema_registry.get_latest_version(field["subject"])
        except SchemaRegistryError:
            raise KafkaClientBootstrapException(
                f"Schema not found for subject: {field['subject']}. Use MockSchemaRegistryClient to register schemas. "
                f"Available subjects: {self._schema_registry.get_subjects()}"
            )

        _sns = (
            _get_subject_name_strategy_call(subject_name_strategy)
            if subject_name_strategy
            else _get_subject_name_strategy_call()
        )
        if field["schemaType"] == "JSON":
            json_serializer = JSONSerializer(
                schema_registry_client=self._schema_registry,
                schema_str=reg_schema.schema,
                conf={"auto.register.schemas": False, "use.latest.version": True, "subject.name.strategy": _sns},
            )
            return json_serializer(field["payload"], SerializationContext(topic, MessageField[ftype]))
        elif field["schemaType"] == "AVRO":
            avro_serializer = AvroSerializer(
                self._schema_registry,
                reg_schema.schema,
                conf={"auto.register.schemas": False, "use.latest.version": True, "subject.name.strategy": _sns},
            )
            return avro_serializer(field["payload"], SerializationContext(topic, MessageField[ftype]))
        else:
            raise KafkaClientBootstrapException(f"Unsupported schema type: {field['schemaType']}")

    def _update_assignment(self, partitions: list[confluent_kafka.TopicPartition]) -> None:
        """Helper method to update internal assignment state."""
        # Store the assignment
        self._assignment = partitions.copy()

        # Initialize position tracking for these partitions
        for tp in partitions:
            if tp.topic not in self._positions:
                self._positions[tp.topic] = {}

            # If an offset was provided, use it, otherwise set to beginning/end based on auto.offset.reset
            if tp.offset > -1:  # Valid offset provided
                self._positions[tp.topic][tp.partition] = tp.offset
            else:
                # Determine offset based on auto.offset.reset
                offset = self._get_initial_offset(tp.topic, tp.partition)
                self._positions[tp.topic][tp.partition] = offset

        self.logger.debug("Updated assignment: %s", self._assignment)

    def _get_initial_offset(self, topic: str, partition: int) -> int:
        """Determine the initial offset for a partition based on auto.offset.reset."""
        # Find the topic in the simulator
        kafka_topic = next((t for t in self._kafka_simulator.topics if t.name == topic), None)
        if kafka_topic is None:
            return 0

        # Get the high watermark
        partition_obj = kafka_topic.partitions[partition]
        high_watermark = len(partition_obj)

        # Determine the offset based on auto.offset.reset
        if self._auto_offset_reset == "earliest":
            return 0
        elif self._auto_offset_reset == "latest":
            return high_watermark
        else:  # Default to latest
            return high_watermark

    def assign(self, partitions: list[confluent_kafka.TopicPartition]) -> None:
        """
        Set the consumer partition assignment to the provided list of confluent_kafka.TopicPartition.

        :param partitions: list of topic+partitions and optionally initial offsets to start consuming from.
        :raises: KafkaException
        """
        # Clear current subscription if any
        if self._subscription:
            self.unsubscribe()

        # Update the assignment
        self._update_assignment(partitions)

        # Notify the simulator of the manual assignment
        self._kafka_simulator.assign_partitions(id(self), partitions)

        self.logger.debug("Manually assigned partitions: %s", self._assignment)

    def assignment(self) -> list[confluent_kafka.TopicPartition]:
        """
        Returns the current partition assignment.

        :returns: list of assigned topic+partitions.
        :rtype: list(confluent_kafka.TopicPartition)
        """
        return self._assignment.copy()

    def close(self) -> None:
        """
        Close down and terminate the Kafka Consumer.

        Actions performed:
        - Stops consuming.
        - Commits offsets, unless the consumer property 'enable.auto.commit' is set to False.
        - Leaves the consumer group.
        """
        # Auto-commit if enabled
        if self._enable_auto_commit and self._assignment:
            self.commit()

        # Leave the consumer group
        if self._subscription:
            # This will be implemented when we extend KafkaSimulator
            pass

        self.logger.info("KConsumer closed, id: %s, group: %s", id(self), self._group_id)

    def consume(self, num_messages: int = 1, timeout: float = -1.0) -> list[KMessage]:
        """
        Consumes a list of messages (possibly empty on timeout).

        :param num_messages: The maximum number of messages to return.
        :param timeout: The maximum time to block waiting for message, event or callback.
        :returns: A list of Message objects (possibly empty on timeout)
        :raises ValueError: if num_messages > 1M
        """
        if num_messages > 1000000:  # 1M limit, same as real Kafka client
            raise ValueError("num_messages must be <= 1000000")

        if not self._assignment:
            self.logger.debug("Consume called but no partitions assigned")
            return []

        # For indefinite timeout
        if timeout == -1.0:
            timeout = None

        # Create a function to fetch messages with a timeout
        def fetch_messages():
            return self._consume_messages(num_messages)

        # Handle timeout
        if timeout is not None and timeout > 0:
            try:
                return self._run_with_timeout_blocking(fetch_messages, timeout=timeout)
            except KConsumerTimeoutException:
                return []
        else:
            return fetch_messages()

    def commit(
        self,
        message: Optional[KMessage] = None,
        offsets: Optional[list[confluent_kafka.TopicPartition]] = None,
        asynchronous: bool = True,
    ) -> Optional[list[confluent_kafka.TopicPartition]]:
        """
        Commit a message or a list of offsets. This behaviour actually differs from the real Kafka client, as in reality
        Consumer does not write to `__consumer_offsets` topic directly, but rather uses the group coordinator to
        commit offsets.

        :param message: Commit the message's offset+1.
        :param offsets: list of topic+partitions+offsets to commit.
        :param asynchronous: If true, asynchronously commit, returning None immediately.
        :returns: None if asynchronous, otherwise the committed offsets.
        """
        offsets_to_commit: list[confluent_kafka.TopicPartition] = []

        # If message is provided, create an offset for it
        if message is not None:
            offsets_to_commit.append(
                confluent_kafka.TopicPartition(message.topic(), message.partition(), message.offset() + 1)
            )
        # If offsets are provided, use them
        elif offsets is not None:
            offsets_to_commit = offsets
        # Otherwise, commit current positions
        else:
            for topic, partitions in self._positions.items():
                for partition, offset in partitions.items():
                    offsets_to_commit.append(confluent_kafka.TopicPartition(topic, partition, offset))

        if offsets_to_commit:
            self._commit_offsets_async(offsets_to_commit)
            if not asynchronous:
                self._tick_buffer()
                return offsets_to_commit

        return None

    def poll(self, timeout: Optional[float] = None) -> Optional[KMessage]:
        """
        Consumes a single message, calls callbacks and returns events.

        :param timeout: Maximum time to block waiting for message, event or callback.
        :returns: A Message object or None on timeout
        """
        if not self._assignment:
            self.logger.debug("Poll called but no partitions assigned")
            return None

        # Convert timeout to milliseconds, -1 for indefinite
        # timeout_ms = -1 if timeout is None else int(timeout * 1000)

        # Create a function to fetch messages with a timeout
        def fetch_message():
            messages = self._consume_messages(1)
            return messages[0] if messages else None

        # Handle timeout
        if timeout is not None and timeout > 0:
            try:
                return self._run_with_timeout_blocking(fetch_message, timeout=timeout)
            except KConsumerTimeoutException:
                return None
        else:
            return fetch_message()

    def _maybe_auto_commit(self):
        """Auto-commit offsets if enabled and it's time to commit."""
        if self._positions:
            offsets_to_commit = []
            for topic, partitions in self._positions.items():
                for partition, offset in partitions.items():
                    offsets_to_commit.append(confluent_kafka.TopicPartition(topic, partition, offset))

            if offsets_to_commit:
                self._commit_offsets_async(offsets_to_commit)

    def _fetch_with_retry(self, request: tuple[int, list[confluent_kafka.TopicPartition], int]) -> list[KMessage]:
        """
        Fetch messages from simulator with retry mechanism.

        :param request: Tuple of (consumer_id, topic_partitions, max_records)
        :returns: List of messages (empty if none available)
        :raises KConsumerMaxRetryException: If max retries exceeded
        """
        count = 0
        while count < self._max_retry_count:
            if getgeneratorstate(self._kafka_simulator.consumers_handler) == GEN_SUSPENDED:
                # Send the request and get the result
                result = self._kafka_simulator.consumers_handler.send(request)

                # Handle the case where generator returns a signal instead of messages
                if hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
                    # It's a list of messages
                    messages = result
                    self.logger.debug("KConsumer(%d): received %d messages", id(self), len(messages))
                    return messages
                else:
                    # It's likely a signal, return empty list
                    self.logger.debug("KConsumer(%d): received signal %s, returning empty list", id(self), result)
                    return []
            else:
                self.logger.info("KConsumer(%d): consumer handler is busy", id(self))
                count += 1
                sleep(count**2 * self._retry_backoff)
        else:
            raise KConsumerMaxRetryException(f"Exceeded max consume retries ({self._max_retry_count})")

    def _consume_messages(self, num_messages: int) -> list[KMessage]:
        """
        Abstract method to consume messages from assigned partitions.

        :param num_messages: Maximum number of messages to consume
        :returns: List of consumed messages
        """
        # Build the topic partitions list with current offsets
        topic_partitions = []
        for tp in self._assignment:
            current_offset = -1
            if tp.topic in self._positions and tp.partition in self._positions[tp.topic]:
                current_offset = self._positions[tp.topic][tp.partition]
            topic_partitions.append(confluent_kafka.TopicPartition(tp.topic, tp.partition, current_offset))

        # Create the request tuple for the simulator
        request = (id(self), topic_partitions, num_messages)

        # Use fetch_with_retry for actual communication
        messages = self._fetch_with_retry(request)

        # Update positions and handle auto-commit if we got messages
        if messages:
            self._update_positions_and_commit(messages)

        return messages

    def _update_positions_and_commit(self, messages: list[KMessage]) -> None:
        """
        Update internal positions and handle auto-commit after consuming messages.

        :param messages: List of consumed messages
        """
        # Update positions for these partitions
        for message in messages:
            if message.topic() not in self._positions:
                self._positions[message.topic()] = {}
            self._positions[message.topic()][message.partition()] = message.offset() + 1

        # Maybe auto-commit the offsets
        if self._enable_auto_commit:
            self._maybe_auto_commit()

    def _on_partition_assign(self, assignment: list[confluent_kafka.TopicPartition]) -> None:
        """Handle assignment of new partitions."""
        # Update our internal state with the new assignment
        self._update_assignment(assignment)

        # If callback is set, call on_assign
        if self._on_assign:
            try:
                self._on_assign(self, assignment)
            except Exception as e:
                self.logger.error("Error in on_assign callback: %s", e)

        self.logger.debug("Assigned partitions: %s", assignment)

    def _on_partition_revoke(self, revoked: list[confluent_kafka.TopicPartition]) -> None:
        """Handle revocation of partitions."""
        # If callback is set, call on_revoke
        if self._on_revoke:
            try:
                self._on_revoke(self, revoked)
            except Exception as e:
                self.logger.error("Error in on_revoke callback: %s", e)

        self.logger.debug("Revoked partitions: %s", revoked)

    def _on_partition_lost(self, lost: list[confluent_kafka.TopicPartition]) -> None:
        """Handle lost partitions."""
        # If lost callback is set, call it
        if self._on_lost:
            try:
                self._on_lost(self, lost)
            except Exception as e:
                self.logger.error("Error in on_lost callback: %s", e)
        # Otherwise, use on_revoke as a fallback
        elif self._on_revoke:
            try:
                self._on_revoke(self, lost)
            except Exception as e:
                self.logger.error("Error in on_revoke callback (for lost partitions): %s", e)

        self.logger.debug("Lost partitions: %s", lost)

    def subscribe(
        self,
        topics: list[str],
        on_assign: Optional[Callable] = None,
        on_revoke: Optional[Callable] = None,
        on_lost: Optional[Callable] = None,
    ) -> None:
        """
        Set subscription to supplied list of topics.
        This replaces a previous subscription.

        :param topics: list of topics (strings) to subscribe to.
        :param on_assign: Callback for partition assignment.
        :param on_revoke: Callback for partition revocation.
        :param on_lost: Callback for lost partitions.
        """
        # Clear current assignment if any
        if self._assignment:
            self.unassign()

        # If already subscribed to different topics, unsubscribe first
        if self._subscription:
            # If callbacks are set, call on_revoke
            old_assignment = self._assignment.copy()
            if old_assignment and self._on_revoke:
                self._on_partition_revoke(old_assignment)

            # Unregister from the consumer group
            self._kafka_simulator.unregister_consumer(id(self))

        # Store the subscription and callbacks
        self._subscription = topics.copy()
        self._on_assign = on_assign
        self._on_revoke = on_revoke
        self._on_lost = on_lost

        # Register with consumer group coordinator
        self._kafka_simulator.register_consumer(id(self), self._group_id, topics)

        # Get our assignment from the simulator (this will trigger a rebalance)
        assignment = self._kafka_simulator.get_member_assignment(id(self))

        # Handle the new assignment
        if assignment:
            self._on_partition_assign(assignment)

        self.logger.debug("Subscribed to topics: %s", self._subscription)

    def unassign(self) -> None:
        """
        Removes the current partition assignment and stops consuming.
        """
        if not self._assignment:
            return

        # Make a copy of the current assignment
        old_assignment = self._assignment.copy()

        # If callbacks are set and we're in subscription mode, call on_revoke
        if self._subscription and old_assignment:
            self._on_partition_revoke(old_assignment)

        # Clear the assignment
        self._assignment = []

        # Clear position tracking for these partitions
        self._positions = {}

        # Notify the simulator
        self._kafka_simulator.assign_partitions(id(self), [])

        self.logger.debug("Unassigned all partitions")

    def unsubscribe(self) -> None:
        """
        Remove current subscription.
        """
        if not self._subscription:
            return

        # Make a copy of the current assignment
        old_assignment = self._assignment.copy()

        # If we have an active assignment from this subscription, revoke it
        if old_assignment:
            self._on_partition_revoke(old_assignment)

        # Clear the subscription and assignment
        self._subscription = []
        self._assignment = []

        # Clear position tracking
        self._positions = {}

        # Leave the consumer group
        self._kafka_simulator.unregister_consumer(id(self))

        self.logger.debug("Unsubscribed from all topics")

    def incremental_assign(self, partitions: list[confluent_kafka.TopicPartition]) -> None:
        """
        Incrementally add the provided list of confluent_kafka.TopicPartition to the current partition assignment.

        :param partitions: list of topic+partitions and optionally initial offsets to start consuming from.
        :raises: KafkaException
        """
        if not partitions:
            return

        # Check for duplicates with the current assignment
        for tp in partitions:
            if any(a.topic == tp.topic and a.partition == tp.partition for a in self._assignment):
                raise confluent_kafka.KafkaException(
                    confluent_kafka.KafkaError(
                        confluent_kafka.KafkaError._INVALID_ARG,
                        f"Duplicate partition in incremental assignment: {tp.topic}[{tp.partition}]",
                        fatal=False,
                    )
                )

        # Add to the current assignment
        new_assignment = self._assignment + partitions

        # Update the positions for the new partitions
        for tp in partitions:
            if tp.topic not in self._positions:
                self._positions[tp.topic] = {}

            # If an offset was provided, use it
            if tp.offset > -1:
                self._positions[tp.topic][tp.partition] = tp.offset
            else:
                # Determine offset based on auto.offset.reset
                offset = self._get_initial_offset(tp.topic, tp.partition)
                self._positions[tp.topic][tp.partition] = offset

        # Update the assignment
        self._assignment = new_assignment

        # Notify the simulator (only if not in a rebalance)
        if not self._subscription:
            self._kafka_simulator.assign_partitions(id(self), new_assignment)

        # Call on_assign callback only for the newly assigned partitions
        if self._on_assign:
            try:
                self._on_assign(self, partitions)
            except Exception as e:
                self.logger.error("Error in on_assign callback during incremental_assign: %s", e)

        self.logger.debug("Incrementally assigned partitions: %s", partitions)

    def incremental_unassign(self, partitions: list[confluent_kafka.TopicPartition]) -> None:
        """
        Incrementally remove the provided list of confluent_kafka.TopicPartition from the current partition assignment.

        :param partitions: list of topic+partitions to remove from the current assignment.
        :raises: KafkaException
        """
        if not partitions:
            return

        # Check that all partitions are currently assigned
        for tp in partitions:
            if not any(a.topic == tp.topic and a.partition == tp.partition for a in self._assignment):
                raise confluent_kafka.KafkaException(
                    confluent_kafka.KafkaError(
                        confluent_kafka.KafkaError._INVALID_ARG,
                        f"Cannot remove partition that is not assigned: {tp.topic}[{tp.partition}]",
                        fatal=False,
                    )
                )

        # Call on_revoke callback for the partitions being removed
        if self._on_revoke:
            try:
                self._on_revoke(self, partitions)
            except Exception as e:
                self.logger.error("Error in on_revoke callback during incremental_unassign: %s", e)

        # Remove from the current assignment
        new_assignment = [
            a
            for a in self._assignment
            if not any(p.topic == a.topic and p.partition == a.partition for p in partitions)
        ]

        # Remove from the positions
        for tp in partitions:
            if tp.topic in self._positions and tp.partition in self._positions[tp.topic]:
                del self._positions[tp.topic][tp.partition]

                # Clean up empty topic entries
                if not self._positions[tp.topic]:
                    del self._positions[tp.topic]

        # Update the assignment
        self._assignment = new_assignment

        # Notify the simulator (only if not in a rebalance)
        if not self._subscription:
            self._kafka_simulator.assign_partitions(id(self), new_assignment)

        self.logger.debug("Incrementally unassigned partitions: %s", partitions)

    def list_topics(self, topic: Optional[str] = None) -> confluent_kafka.admin.ClusterMetadata:
        """
        Request metadata from the cluster.

        :param topic: If specified, only request information about this topic.
        :returns: ClusterMetadata
        """
        return self._kafka_simulator.get_cluster_mdata(topic)

    def memberid(self) -> str:
        """
        Return this client's broker-assigned group member id.

        :returns: Member id string
        """
        return self._member_id

    def consumer_group_metadata(self):
        """
        Return an opaque object representing the consumer's current group metadata.

        :returns: An object representing the consumer's current group metadata.
        """
        if not self._group_id:
            raise confluent_kafka.KafkaException(
                confluent_kafka.KafkaError(
                    confluent_kafka.KafkaError._STATE,
                    "Consumer group metadata not available (not a group member)",
                    fatal=False,
                )
            )

        # Create a simple metadata object with the group info
        class GroupMetadata:
            def __init__(self, group_id, member_id):
                self.group_id = group_id
                self.member_id = member_id

        return GroupMetadata(self._group_id, self._member_id)

    @staticmethod
    def _timeout_handler(signum: Any, frame: Any) -> None:
        """Handler for SIGALRM signal."""
        raise KConsumerTimeoutException("Timeout exceeded")

    def _run_with_timeout_blocking(self, func, args=(), kwargs=None, timeout: float = 5):
        """
        Run function with timeout and block if finished earlier.
        """
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout)
        start_time = time()
        try:
            result = func(*args, **(kwargs or {}))
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed_time = time() - start_time
            remaining_time = timeout - elapsed_time
            if remaining_time > 0:
                sleep(remaining_time)
        return result

    def committed(self, partitions: list[confluent_kafka.TopicPartition]) -> list[confluent_kafka.TopicPartition]:
        """
        Retrieve committed offsets for the specified partitions.

        :param partitions: list of topic+partitions to query for stored offsets.
        :returns: list of topic+partitions with offset and possibly error set.
        """
        return self._kafka_simulator.get_committed_offsets(id(self), partitions)

    def position(self, partitions: list[confluent_kafka.TopicPartition]) -> list[confluent_kafka.TopicPartition]:
        """
        Retrieve current positions (offsets) for the specified partitions.

        :param partitions: list of topic+partitions to return current offsets for.
        :returns: list of topic+partitions with offset and possibly error set.
        """
        result = []
        for tp in partitions:
            current_offset = -1
            if tp.topic in self._positions and tp.partition in self._positions[tp.topic]:
                current_offset = self._positions[tp.topic][tp.partition]
            result.append(confluent_kafka.TopicPartition(tp.topic, tp.partition, current_offset))
        return result

    def seek(self, partition: confluent_kafka.TopicPartition) -> None:
        """
        Set consume position for partition to offset.

        :param partition: Topic+partition+offset to seek to.
        """
        if not self._assignment:
            raise confluent_kafka.KafkaException(
                confluent_kafka.KafkaError(
                    confluent_kafka.KafkaError._STATE,
                    "Cannot seek on consumer without assignment",
                    fatal=True,
                )
            )

        # Check if this partition is in our assignment
        if not any(tp.topic == partition.topic and tp.partition == partition.partition for tp in self._assignment):
            raise confluent_kafka.KafkaException(
                confluent_kafka.KafkaError(
                    confluent_kafka.KafkaError._UNKNOWN_PARTITION,
                    f"Cannot seek on unassigned partition: {partition.topic}[{partition.partition}]",
                    fatal=True,
                )
            )

        # Update our position for this partition
        if partition.topic not in self._positions:
            self._positions[partition.topic] = {}
        self._positions[partition.topic][partition.partition] = partition.offset

        # Notify the simulator of the seek operation
        if getgeneratorstate(self._kafka_simulator.consumers_handler) == GEN_SUSPENDED:
            self._kafka_simulator.consumers_handler.send(partition)

        self.logger.debug("Seek to offset %d for %s[%d]", partition.offset, partition.topic, partition.partition)

    def store_offsets(
        self, message: Optional[KMessage] = None, offsets: Optional[list[confluent_kafka.TopicPartition]] = None
    ) -> None:
        """
        Store offsets for a message or a list of offsets.

        :param message: Store message's offset+1.
        :param offsets: list of topic+partitions+offsets to store.
        """
        if self._enable_auto_offset_store:
            raise confluent_kafka.KafkaException(
                confluent_kafka.KafkaError(
                    confluent_kafka.KafkaError.INVALID_CONFIG,
                    "store_offsets() requires 'enable.auto.offset.store=False'",
                    fatal=False,
                )
            )

        stored_offsets = []

        # If message is provided, store its offset
        if message is not None:
            stored_offsets.append(
                confluent_kafka.TopicPartition(message.topic(), message.partition(), message.offset() + 1)
            )

        # If offsets are provided, store them
        elif offsets is not None:
            stored_offsets = offsets

        # Update our positions with these offsets
        for tp in stored_offsets:
            if tp.topic not in self._positions:
                self._positions[tp.topic] = {}
            self._positions[tp.topic][tp.partition] = tp.offset

        self.logger.debug("Stored offsets: %s", stored_offsets)

    def pause(self, partitions: list[confluent_kafka.TopicPartition]) -> None:
        """
        Pause consumption for the provided list of partitions.

        :param partitions: list of topic+partitions to pause.
        """
        # Add each partition to the paused list if it's not already there
        for tp in partitions:
            if not any(p.topic == tp.topic and p.partition == tp.partition for p in self._paused_partitions):
                self._paused_partitions.append(tp)

        self.logger.debug("Paused partitions: %s", self._paused_partitions)

    def resume(self, partitions: list[confluent_kafka.TopicPartition]) -> None:
        """
        Resume consumption for the provided list of partitions.

        :param partitions: list of topic+partitions to resume.
        """
        # Remove each partition from the paused list
        self._paused_partitions = [
            p
            for p in self._paused_partitions
            if not any(tp.topic == p.topic and tp.partition == p.partition for tp in partitions)
        ]

        self.logger.debug("Resumed partitions, still paused: %s", self._paused_partitions)

    def get_watermark_offsets(self, partition: confluent_kafka.TopicPartition) -> Optional[tuple[int, int]]:
        """
        Retrieve low and high offsets for the specified partition.

        :param partition: Topic+partition to return offsets for.
        :returns: tuple of (low,high) on success or None on timeout.
        """
        # Find the topic
        topic = next((t for t in self._kafka_simulator.topics if t.name == partition.topic), None)
        if topic is None or partition.partition >= len(topic.partitions):
            raise confluent_kafka.KafkaException(
                confluent_kafka.KafkaError(
                    confluent_kafka.KafkaError._UNKNOWN_PARTITION,
                    f"Unknown partition: {partition.topic}[{partition.partition}]",
                    fatal=False,
                )
            )

        # Get the partition
        kafka_partition = topic.partitions[partition.partition]

        # Get the low and high offsets
        low_offset = 0  # In a real Kafka cluster, this would be the oldest available message
        high_offset = len(kafka_partition)  # Next offset to be produced

        return low_offset, high_offset

    def _send_with_retry(self, message: KMessage) -> None:
        """Send message to buffer handler with retry mechanism."""
        count = 0
        while count < self._max_retry_count:
            if getgeneratorstate(self._buffer_handler) == GEN_SUSPENDED:
                ack = self._buffer_handler.send(message)
                self.logger.debug("KConsumer(%d): received ack: %s", id(self), ack)
                break
            else:
                self.logger.debug("KConsumer(%d): buffer is busy", id(self))
                count += 1
                sleep(count**2 * self._retry_backoff)
        else:
            raise KConsumerMaxRetryException(f"Exceeded max send retries ({self._max_retry_count})")

    def _tick_buffer(self):
        """
        Sends `DONE` signal to message buffer handler in order to force sending buffered messages to Kafka Simulator.
        """
        try_count = 0
        while try_count < self._max_retry_count:
            if getgeneratorstate(self._buffer_handler) == GEN_SUSPENDED:
                self._buffer_handler.send(Tick.DONE)
                break
            else:
                try_count += 1
                sleep(try_count**2 * self._retry_backoff)
        else:
            raise KConsumerMaxRetryException(f"Exceeded max send retries ({self._max_retry_count})")

    def _commit_offsets_async(self, offsets: list[confluent_kafka.TopicPartition]) -> None:
        """Commit offsets to the __consumer_offsets topic."""
        for offset in offsets:
            key = f"{self._group_id}:{offset.topic}:{offset.partition}".encode()
            value = str(offset.offset).encode()
            self._send_with_retry(KMessage("__consumer_offsets", -1, key, value))

        self.logger.debug("Committed offsets: %s", offsets)

    def __del__(self):
        if hasattr(self, "config"):  # if __init__ was called without exceptions
            try:
                self.close()
            except Exception as e:
                self.logger.error("Error during KConsumer destruction: %s", e)

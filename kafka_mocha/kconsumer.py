from typing import Any, Optional, Literal

import confluent_kafka

from kafka_mocha import validate_config
from kafka_mocha.klogger import get_custom_logger


class KConsumer:
    def __init__(
        self,
        config: dict[str, Any],
        input: Optional[list[str]] = None,
        loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING",
    ):
        validate_config("consumer", config)
        self.config = config
        self.input = input
        self.logger = get_custom_logger(loglevel)

    def assign(self, partitions):
        """
        :param list(TopicPartition) partitions: List of topic+partitions and optionally initial offsets to start
            consuming from.
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def assignment(self, *args, **kwargs):
        """Returns the current partition assignment.

        :returns: List of assigned topic+partitions.
        :rtype: list(TopicPartition)
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def close(self, *args, **kwargs):
        """
        Close down and terminate the Kafka Consumer.

        Actions performed:
            - Stops consuming.
            - Commits offsets, unless the consumer property 'enable.auto.commit' is set to False.
            - Leaves the consumer group.

        :note: Registered callbacks may be called from this method, see :py:func::`poll()` for more info.
        :rtype: None
        """
        pass

    def commit(self, message=None, *args, **kwargs):
        """Commit a message or a list of offsets.  commit([message=None], [offsets=None], [asynchronous=True])

        The ``message`` and ``offsets`` parameters are mutually exclusive. If neither is set, the current partition
        assignment's offsets are used instead. Use this method to commit offsets if you have 'enable.auto.commit'
        set to False.

        :param confluent_kafka.Message message: Commit the message's offset+1. Note: By convention, committed offsets
            reflect the next message to be consumed, **not** the last message consumed.
        :param list(TopicPartition) offsets: List of topic+partitions+offsets to commit.
        :param bool asynchronous: If true, asynchronously commit, returning None immediately. If False, the commit()
            call will block until the commit succeeds or fails and the committed offsets will be returned (on success).
            Note that specific partitions may have failed and the .err field of each partition should be checked for
            success.
        :rtype: None|list(TopicPartition)
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def committed(self, partitions, timeout=None):
        """Retrieve committed offsets for the specified partitions. committed(partitions, [timeout=None])

        :param list(TopicPartition) partitions: List of topic+partitions to query for stored offsets.
        :param float timeout: Request timeout (seconds).
        :returns: List of topic+partitions with offset and possibly error set.
        :rtype: list(TopicPartition)
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def consume(self, num_messages=1, *args, **kwargs):
        """Consumes a list of messages (possibly empty on timeout). Callbacks may be executed as a side effect of
        calling this method. consume([num_messages=1], [timeout=-1])

        The application must check the returned :py:class:`Message` object's :py:func:`Message.error()` method to
        distinguish between proper messages (error() returns None) and errors for each :py:class:`Message` in the list
        (see error().code() for specifics). If the enable.partition.eof configuration property is set to True,
        partition EOF events will also be exposed as Messages with error().code() set to _PARTITION_EOF.

        :note: Callbacks may be called from this method, such as ``on_assign``, ``on_revoke``

        :param int num_messages: The maximum number of messages to return (default: 1).
        :param float timeout: The maximum time to block waiting for message, event or callback
            (default: infinite (-1)). (Seconds)
        :returns: A list of Message objects (possibly empty on timeout)
        :rtype: list(Message)
        :raises RuntimeError: if called on a closed consumer
        :raises KafkaError: in case of internal error
        :raises ValueError: if num_messages > 1M
        """
        pass

    def consumer_group_metadata(self):
        """consumer_group_metadata()

        :returns: An opaque object representing the consumer's current group metadata for passing to the transactional
        producer's send_offsets_to_transaction() API.
        """
        pass

    def get_watermark_offsets(self, partition, timeout=None, *args, **kwargs):
        """Retrieve low and high offsets for the specified partition.
        get_watermark_offsets(partition, [timeout=None], [cached=False])

        :param TopicPartition partition: Topic+partition to return offsets for.
        :param float timeout: Request timeout (seconds). Ignored if cached=True.
        :param bool cached: Instead of querying the broker, use cached information. Cached values: The low offset is
            updated periodically (if statistics.interval.ms is set) while the high offset is updated on each message
            fetched from the broker for this partition.
        :returns: Tuple of (low,high) on success or None on timeout. The high offset is the offset of the last
            message + 1.
        :rtype: tuple(int,int)
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def incremental_assign(self, partitions):
        """Incrementally add the provided list of :py:class:`TopicPartition` to the current partition assignment.
        This list must not contain duplicate entries, or any entry corresponding to an already assigned partition. When
        a COOPERATIVE assignor (i.e. incremental rebalancing) is being used, this method may be used in the on_assign
        callback to update the current assignment and specify start offsets. The application should pass a list of
        partitions identical to the list passed to the callback, even if the list is empty. Note that if you do not call
        incremental_assign in your on_assign handler, this will be done automatically and start offsets will be the last
        committed offsets, or determined via the auto offset reset policy (auto.offset.reset) if there are none. This
        method may also be used outside the context of a rebalance callback.


        :param list(TopicPartition) partitions: List of topic+partitions and optionally initial offsets to start
            consuming from.
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def incremental_unassign(self, partitions):
        """Incrementally remove the provided list of :py:class:`TopicPartition` from the current partition assignment.
        This list must not contain dupliate entries and all entries specified must be part of the current assignment.
        When a COOPERATIVE assignor (i.e. incremental rebalancing) is being used, this method may be used in the
        on_revoke or on_lost callback to update the current assignment. The application should pass a list of partitions
        identical to the list passed to the callback. This method may also be used outside the context of a rebalance
        callback. The value of the `TopicPartition` offset field is ignored by this method.

        :param list(TopicPartition) partitions: List of topic+partitions to remove from the current assignment.
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def list_topics(self, topic=None, *args, **kwargs):
        """ Request metadata from the cluster. list_topics([topic=None], [timeout=-1])

        This method provides the same information as  listTopics(), describeTopics() and describeCluster() in
        the Java Admin client.

        :param str topic: If specified, only request information about this topic, else return results for all topics in
            cluster. Warning: If auto.create.topics.enable is set to true on the broker and an unknown topic is
            specified, it will be created.
        :param float timeout: The maximum response time before timing out, or -1 for infinite timeout.
        :rtype: ClusterMetadata
        :raises: KafkaException
        """
        pass

    def memberid(self):
        """Return this client's broker-assigned group member id.

        The member id is assigned by the group coordinator and is propagated to the consumer during rebalance.

        :returns: Member id string or None
        :rtype: string
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def offsets_for_times(self, partitions, timeout=None):
        """Look up offsets by timestamp for the specified partitions.

         The returned offset for each partition is the earliest offset whose
         timestamp is greater than or equal to the given timestamp in the
         corresponding partition. If the provided timestamp exceeds that of the
         last message in the partition, a value of -1 will be returned.

         :param list(TopicPartition) partitions: topic+partitions with timestamps in the TopicPartition.offset field.
         :param float timeout: Request timeout (seconds).
         :returns: List of topic+partition with offset field set and possibly error set
         :rtype: list(TopicPartition)
         :raises: KafkaException
         :raises: RuntimeError if called on a closed consumer
        """
        pass

    def pause(self, partitions):
        """Pause consumption for the provided list of partitions.

        :param list(TopicPartition) partitions: List of topic+partitions to pause.
        :rtype: None
        :raises: KafkaException
        """
        pass

    def poll(self, timeout=None):
        """Consumes a single message, calls callbacks and returns events.

        The application must check the returned :py:class:`Message` object's :py:func:`Message.error()` method to
        distinguish between proper messages (error() returns None), or an event or error
        (see error().code() for specifics).

        :note: Callbacks may be called from this method, such as ``on_assign``, ``on_revoke``, et.al.

        :param float timeout: Maximum time to block waiting for message, event or callback
            (default: infinite (None translated into -1 in the library)). (Seconds)
        :returns: A Message object or None on timeout
        :rtype: :py:class:`Message` or None
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def position(self, partitions):
        """Retrieve current positions (offsets) for the specified partitions.

        :param list(TopicPartition) partitions: List of topic+partitions to return current offsets for. The current
            offset is the offset of the last consumed message + 1.
        :returns: List of topic+partitions with offset and possibly error set.
        :rtype: list(TopicPartition)
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def resume(self, partitions):
        """Resume consumption for the provided list of partitions.

        :param list(TopicPartition) partitions: List of topic+partitions to resume.
        :rtype: None
        :raises: KafkaException
        """
        pass

    def seek(self, partition):
        """
        Set consume position for partition to offset. The offset may be an absolute (>=0)
        or a logical offset (:py:const:`OFFSET_BEGINNING` et.al).

        Set consume position for partition to offset.
        The offset may be an absolute (>=0) or a
        logical offset (:py:const:`OFFSET_BEGINNING` et.al).

        seek() may only be used to update the consume offset of an
        actively consumed partition (i.e., after :py:const:`assign()`),
        to set the starting offset of partition not being consumed instead
        pass the offset in an `assign()` call.

        :param TopicPartition partition: Topic+partition+offset to seek to.
        :raises: KafkaException
        """
        pass

    def set_sasl_credentials(self, username, password):
        """Sets the SASL credentials used for this client.

        These credentials will overwrite the old ones, and will be used the next time the client needs to authenticate.
        This method will not disconnect existing broker connections that have been established with the old credentials.
        This method is applicable only to SASL PLAIN and SCRAM mechanisms.
        """
        pass

    def store_offsets(self, message=None, *args, **kwargs):
        """Store offsets for a message or a list of offsets.

        ``message`` and ``offsets`` are mutually exclusive. The stored offsets will be committed according to
        'auto.commit.interval.ms' or manual offset-less :py:meth:`commit`. Note that 'enable.auto.offset.store' must be
        set to False when using this API.

        :param confluent_kafka.Message message: Store message's offset+1.
        :param list(TopicPartition) offsets: List of topic+partitions+offsets to store.
        :rtype: None
        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

    def subscribe(self, topics, on_assign=None, *args, **kwargs):
        """Set subscription to supplied list of topics. This replaces a previous subscription.
        :py:function:: subscribe(topics, [on_assign=None], [on_revoke=None], [on_lost=None])

        Regexp pattern subscriptions are supported by prefixing the topic string with ``"^"``, e.g.::
            consumer.subscribe(["^my_topic.*", "^another[0-9]-?[a-z]+$", "not_a_regex"])

        :param list(str) topics: List of topics (strings) to subscribe to.
        :param callable on_assign: callback to provide handling of customized offsets on completion of a successful
            partition re-assignment.
        :param callable on_revoke: callback to provide handling of offset commits to a customized store on the start of
            a rebalance operation.
        :param callable on_lost: callback to provide handling in the case the partition assignment has been lost. If not
            specified, lost partition events will be delivered to on_revoke, if specified. Partitions that have been
            lost may already be owned by other members in the group and therefore committing offsets, for example,
            may fail.
        :raises KafkaException:
        :raises: RuntimeError if called on a closed consumer

        :py:function:: on_assign(consumer, partitions)
        :py:function:: on_revoke(consumer, partitions)
        :py:function:: on_lost(consumer, partitions)

        :param Consumer consumer: Consumer instance.
        :param list(TopicPartition) partitions: Absolute list of partitions being assigned or revoked.
        """
        pass

    def unassign(self, *args, **kwargs):
        """Removes the current partition assignment and stops consuming.

        :raises KafkaException:
        :raises RuntimeError: if called on a closed consumer
        """
        pass

    def unsubscribe(self, *args, **kwargs):
        """Remove current subscription.

        :raises: KafkaException
        :raises: RuntimeError if called on a closed consumer
        """
        pass

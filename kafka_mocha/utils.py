from typing import Any, Literal

from kafka_mocha.exceptions import KafkaClientBootstrapException

common_config_schema = {
    "builtin.features": {"type": str, "allowed": None},
    "client.id": {"type": str, "allowed": None},
    "metadata.broker.list": {"type": str, "allowed": None},
    "bootstrap.servers": {"type": str, "allowed": None},
    "message.max.bytes": {"type": int, "range": (1000, 1000000000)},
    "message.copy.max.bytes": {"type": int, "range": (0, 1000000000)},
    "receive.message.max.bytes": {"type": int, "range": (1000, 2147483647)},
    "max.in.flight.requests.per.connection": {"type": int, "range": (1, 1000000)},
    "max.in.flight": {"type": int, "range": (1, 1000000)},
    "topic.metadata.refresh.interval.ms": {"type": int, "range": (-1, 3600000)},
    "metadata.max.age.ms": {"type": int, "range": (1, 86400000)},
    "topic.metadata.refresh.fast.interval.ms": {"type": int, "range": (1, 60000)},
    "topic.metadata.refresh.fast.cnt": {"type": int, "range": (0, 1000)},
    "topic.metadata.refresh.sparse": {"type": bool, "allowed": [True, False]},
    "topic.metadata.propagation.max.ms": {"type": int, "range": (0, 3600000)},
    "topic.blacklist": {"type": str, "allowed": None},
    "debug": {"type": str, "allowed": None},
    "socket.timeout.ms": {"type": int, "range": (10, 300000)},
    "socket.blocking.max.ms": {"type": int, "range": (1, 60000)},
    "socket.send.buffer.bytes": {"type": int, "range": (0, 100000000)},
    "socket.receive.buffer.bytes": {"type": int, "range": (0, 100000000)},
    "socket.keepalive.enable": {"type": bool, "allowed": [True, False]},
    "socket.nagle.disable": {"type": bool, "allowed": [True, False]},
    "socket.max.fails": {"type": int, "range": (0, 1000000)},
    "broker.address.ttl": {"type": int, "range": (0, 86400000)},
    "broker.address.family": {"type": str, "allowed": ["any", "v4", "v6"]},
    "socket.connection.setup.timeout.ms": {"type": int, "range": (1000, 2147483647)},
    "connections.max.idle.ms": {"type": int, "range": (0, 2147483647)},
    "reconnect.backoff.ms": {"type": int, "range": (0, 3600000)},
    "reconnect.backoff.max.ms": {"type": int, "range": (0, 3600000)},
    "statistics.interval.ms": {"type": int, "range": (0, 86400000)},
    "enabled_events": {"type": int, "range": (0, 2147483647)},
    "log_level": {"type": int, "range": (0, 7)},
    "log.queue": {"type": bool, "allowed": [True, False]},
    "log.thread.name": {"type": bool, "allowed": [True, False]},
    "enable.random.seed": {"type": bool, "allowed": [True, False]},
    "log.connection.close": {"type": bool, "allowed": [True, False]},
    "internal.termination.signal": {"type": int, "range": (0, 128)},
    "api.version.request": {"type": bool, "allowed": [True, False]},
    "api.version.request.timeout.ms": {"type": int, "range": (1, 300000)},
    "api.version.fallback.ms": {"type": int, "range": (0, 604800000)},
    "broker.version.fallback": {"type": str, "allowed": None},
    "security.protocol": {"type": str, "allowed": ["plaintext", "ssl", "sasl_plaintext", "sasl_ssl"]},
    "retry.backoff.ms": {"type": int, "range": (1, 300000)},
    "retry.backoff.max.ms": {"type": int, "range": (1, 300000)},
    "client.dns.lookup": {"type": str, "allowed": ["use_all_dns_ips", "resolve_canonical_bootstrap_servers_only"]},
    "enable.metrics.push": {"type": bool, "allowed": [True, False]},
}
producer_config_schema = {
    "transactional.id": {"type": str, "allowed": None},
    "transaction.timeout.ms": {"type": int, "range": (1000, 2147483647)},
    "enable.idempotence": {"type": bool, "allowed": [True, False]},
    "enable.gapless.guarantee": {"type": bool, "allowed": [True, False]},
    "queue.buffering.max.messages": {"type": int, "range": (0, 2147483647)},
    "queue.buffering.max.kbytes": {"type": int, "range": (1, 2147483647)},
    "queue.buffering.max.ms": {"type": int, "range": (0, 900000)},
    "linger.ms": {"type": int, "range": (0, 900000)},
    "message.send.max.retries": {"type": int, "range": (0, 2147483647)},
    "retries": {"type": int, "range": (0, 2147483647)},
    "retry.backoff.ms": {"type": int, "range": (1, 300000)},
    "retry.backoff.max.ms": {"type": int, "range": (1, 300000)},
    "queue.buffering.backpressure.threshold": {"type": int, "range": (1, 1000000)},
    "compression.codec": {"type": str, "allowed": ["none", "gzip", "snappy", "lz4", "zstd"]},
    "compression.type": {"type": str, "allowed": ["none", "gzip", "snappy", "lz4", "zstd"]},
    "batch.num.messages": {"type": int, "range": (1, 1000000)},
    "batch.size": {"type": int, "range": (1, 2147483647)},
    "delivery.report.only.error": {"type": bool, "allowed": [True, False]},
    "dr_cb": {"type": str, "allowed": None},  # Assuming type string for callback
    "dr_msg_cb": {"type": str, "allowed": None},  # Assuming type string for callback
    "sticky.partitioning.linger.ms": {"type": int, "range": (0, 900000)},
    "request.required.acks": {"type": int, "range": (-1, 1000)},
    "acks": {"type": int, "range": (-1, 1000)},
    "request.timeout.ms": {"type": int, "range": (1, 900000)},
    "message.timeout.ms": {"type": int, "range": (0, 2147483647)},
    "delivery.timeout.ms": {"type": int, "range": (0, 2147483647)},
    "queuing.strategy": {"type": str, "allowed": ["fifo", "lifo"]},
    "produce.offset.report": {"type": bool, "allowed": [True, False]},
    "partitioner": {"type": str, "allowed": None},  # Assuming type string for partitioner
    "partitioner_cb": {"type": str, "allowed": None},  # Assuming type string for callback
    "msg_order_cmp": {"type": str, "allowed": None},  # Assuming type string for callback
}
consumer_config_schema = {
    "group.id": {"type": str, "allowed": None},
    "group.instance.id": {"type": str, "allowed": None},
    "partition.assignment.strategy": {"type": str, "allowed": ["range", "roundrobin"]},
    "session.timeout.ms": {"type": int, "range": (1, 3600000)},
    "heartbeat.interval.ms": {"type": int, "range": (1, 3600000)},
    "group.protocol.type": {"type": str, "allowed": ["consumer"]},
    "group.protocol": {"type": str, "allowed": ["classic", "consumer"]},
    "group.remote.assignor": {"type": str, "allowed": None},
    "coordinator.query.interval.ms": {"type": int, "range": (1, 3600000)},
    "max.poll.interval.ms": {"type": int, "range": (1, 86400000)},
    "enable.auto.commit": {"type": bool, "allowed": [True, False]},
    "auto.commit.interval.ms": {"type": int, "range": (0, 86400000)},
    "enable.auto.offset.store": {"type": bool, "allowed": [True, False]},
    "queued.min.messages": {"type": int, "range": (1, 10000000)},
    "queued.max.messages.kbytes": {"type": int, "range": (1, 2097151)},
    "fetch.wait.max.ms": {"type": int, "range": (0, 300000)},
    "fetch.queue.backoff.ms": {"type": int, "range": (0, 300000)},
    "fetch.message.max.bytes": {"type": int, "range": (1, 1000000000)},
    "max.partition.fetch.bytes": {"type": int, "range": (1, 1000000000)},
    "fetch.max.bytes": {"type": int, "range": (0, 2147483135)},
    "fetch.min.bytes": {"type": int, "range": (1, 100000000)},
    "fetch.error.backoff.ms": {"type": int, "range": (0, 300000)},
    "offset.store.method": {"type": str, "allowed": ["none", "file", "broker"]},
    "isolation.level": {"type": str, "allowed": ["read_uncommitted", "read_committed"]},
    "consume_cb": {"type": str, "allowed": None},  # Assuming type string for callback
    "rebalance_cb": {"type": str, "allowed": None},  # Assuming type string for callback
    "offset_commit_cb": {"type": str, "allowed": None},  # Assuming type string for callback
    "enable.partition.eof": {"type": bool, "allowed": [True, False]},
    "check.crcs": {"type": bool, "allowed": [True, False]},
}


def validate_common_config(config: dict[str, Any]) -> None:
    """Validates common (C/P = *) configuration options for KafkaProducer and KafkaConsumer.

    :param config: Configuration dictionary
    :raises KafkaClientBootstrapException: If configuration is invalid
    """

    if "bootstrap.servers" not in config:
        raise KafkaClientBootstrapException("Configuration validation errors: bootstrap.servers is required")

    errors = []
    for key, value in config.items():
        if key not in common_config_schema:
            errors.append(f"Unknown configuration parameter: {key}")
            continue

        expected_type = common_config_schema[key]["type"]
        if not isinstance(value, expected_type):
            errors.append(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
            continue

        allowed_range = common_config_schema[key].get("range")
        if allowed_range and not (allowed_range[0] <= value <= allowed_range[1]):
            errors.append(f"Value out of range for {key}: expected {allowed_range}, got {value}")
            continue

        allowed_values = common_config_schema[key].get("allowed")
        if allowed_values and value not in allowed_values:
            errors.append(f"Invalid value for {key}: expected one of {allowed_values}, got {value}")
            continue

    if errors:
        raise KafkaClientBootstrapException("Configuration validation errors: " + "; ".join(errors))


def validate_producer_config(config):
    """Validates producer's (C/P = P) configuration options for KafkaProducer.

    :param config: Configuration dictionary
    :raises KafkaClientBootstrapException: If configuration is invalid
    """

    errors = []
    for key, value in config.items():
        if key not in producer_config_schema:
            errors.append(f"Unknown configuration parameter: {key}")
            continue

        expected_type = producer_config_schema[key]["type"]
        if not isinstance(value, expected_type):
            errors.append(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
            continue

        allowed_range = producer_config_schema[key].get("range")
        if allowed_range and not (allowed_range[0] <= value <= allowed_range[1]):
            errors.append(f"Value out of range for {key}: expected {allowed_range}, got {value}")
            continue

        allowed_values = producer_config_schema[key].get("allowed")
        if allowed_values and value not in allowed_values:
            errors.append(f"Invalid value for {key}: expected one of {allowed_values}, got {value}")
            continue

    if errors:
        raise KafkaClientBootstrapException("Configuration validation errors: " + "; ".join(errors))


def validate_consumer_config(config):
    # Configuration schema for consumer (C/P = C) properties

    errors = []

    for key, value in config.items():
        if key not in consumer_config_schema:
            errors.append(f"Unknown configuration parameter: {key}")
            continue

        expected_type = consumer_config_schema[key]["type"]
        if not isinstance(value, expected_type):
            errors.append(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
            continue

        allowed_range = consumer_config_schema[key].get("range")
        if allowed_range and not (allowed_range[0] <= value <= allowed_range[1]):
            errors.append(f"Value out of range for {key}: expected {allowed_range}, got {value}")
            continue

        allowed_values = consumer_config_schema[key].get("allowed")
        if allowed_values and value not in allowed_values:
            errors.append(f"Invalid value for {key}: expected one of {allowed_values}, got {value}")
            continue

    if errors:
        raise KafkaClientBootstrapException("Configuration validation errors: " + "; ".join(errors))


def validate_config(config_type: Literal["common", "producer", "consumer"], config: dict[str, Any]) -> None:
    """Validates configuration options for KafkaProducer and KafkaConsumer.

    :param config_type: Configuration type
    :param config: Configuration dictionary
    :raises KafkaClientBootstrapException: If configuration is invalid
    """

    if config_type == "common":
        validate_common_config(config)
    elif config_type == "producer":
        producer_only_config = {**config}
        for key in common_config_schema.keys():
            producer_only_config.pop(key, None)
        validate_producer_config(producer_only_config)
    else:
        consumer_only_config = {**config}
        for key in common_config_schema.keys():
            consumer_only_config.pop(key, None)
        validate_consumer_config(consumer_only_config)

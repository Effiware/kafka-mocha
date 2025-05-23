from collections.abc import Callable
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
    "security.protocol": {
        "type": str,
        "allowed": ["plaintext", "ssl", "sasl_plaintext", "sasl_ssl", "SSL", "SASL_SSL"],
    },
    "ssl.cipher.suites": {"type": str, "allowed": None},
    "ssl.curves.list": {"type": str, "allowed": None},
    "ssl.sigalgs.list": {"type": str, "allowed": None},
    "ssl.key.location": {"type": str, "allowed": None},
    "ssl.key.password": {"type": str, "allowed": None},
    "ssl.key.pem": {"type": str, "allowed": None},
    "ssl_key": {"type": str, "allowed": None},
    "ssl.certificate.location": {"type": str, "allowed": None},
    "ssl.certificate.pem": {"type": str, "allowed": None},
    "ssl_certificate": {"type": str, "allowed": None},
    "ssl.ca.location": {"type": str, "allowed": None},
    "ssl.ca.pem": {"type": str, "allowed": None},
    "ssl_ca": {"type": str, "allowed": None},
    "ssl.ca.certificate.stores": {"type": str, "allowed": None},
    "ssl.crl.location": {"type": str, "allowed": None},
    "ssl.keystore.location": {"type": str, "allowed": None},
    "ssl.keystore.password": {"type": str, "allowed": None},
    "ssl.providers": {"type": str, "allowed": None},
    "ssl.engine.location": {"type": str, "allowed": None},
    "ssl.engine.id": {"type": str, "allowed": None},
    "ssl_engine_callback_data": {"type": str, "allowed": None},
    "enable.ssl.certificate.verification": {"type": bool, "allowed": [True, False]},
    "ssl.endpoint.identification.algorithm": {"type": str, "allowed": ["none", "https"]},
    "ssl.certificate.verify_cb": {"type": str, "allowed": None},
    "sasl.mechanisms": {"type": str, "allowed": ["GSSAPI", "PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"]},
    "sasl.mechanism": {"type": str, "allowed": ["GSSAPI", "PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"]},
    "sasl.kerberos.service.name": {"type": str, "allowed": None},
    "sasl.kerberos.principal": {"type": str, "allowed": None},
    "sasl.kerberos.kinit.cmd": {"type": str, "allowed": None},
    "sasl.kerberos.keytab": {"type": str, "allowed": None},
    "sasl.kerberos.min.time.before.relogin": {"type": int, "range": (0, 86400000)},
    "sasl.username": {"type": str, "allowed": None},
    "sasl.password": {"type": str, "allowed": None},
    "sasl.oauthbearer.config": {"type": str, "allowed": None},
    "enable.sasl.oauthbearer.unsecure.jwt": {"type": bool, "allowed": [True, False]},
    "oauthbearer_token_refresh_cb": {"type": Callable, "args": 1},
    "sasl.oauthbearer.method": {"type": str, "allowed": ["default", "oidc"]},
    "sasl.oauthbearer.client.id": {"type": str, "allowed": None},
    "sasl.oauthbearer.client.secret": {"type": str, "allowed": None},
    "sasl.oauthbearer.scope": {"type": str, "allowed": None},
    "sasl.oauthbearer.extensions": {"type": str, "allowed": None},
    "sasl.oauthbearer.token.endpoint.url": {"type": str, "allowed": None},
    "plugin.library.paths": {"type": str, "allowed": None},
    "retry.backoff.ms": {"type": int, "range": (1, 300000)},
    "retry.backoff.max.ms": {"type": int, "range": (1, 300000)},
    "client.dns.lookup": {"type": str, "allowed": ["use_all_dns_ips", "resolve_canonical_bootstrap_servers_only"]},
    "enable.metrics.push": {"type": bool, "allowed": [True, False]},
    "error_cb": {"type": Callable, "args": 1},
    "throttle_cb": {"type": Callable, "args": 1},
    "stats_cb": {"type": Callable, "args": 1},
    "oauth_cb": {"type": Callable, "args": 1},
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
    "auto.offset.reset": {"type": str, "allowed": ["earliest", "latest", "error"]},
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
    "consume_cb": {"type": Callable, "args": 1},
    "rebalance_cb": {"type": Callable, "args": 2},
    "offset_commit_cb": {"type": Callable, "args": 1},
    "enable.partition.eof": {"type": bool, "allowed": [True, False]},
    "check.crcs": {"type": bool, "allowed": [True, False]},
    "retries": {"type": int, "range": (0, 2147483647)},
}


def _validate_against_schema(schema: dict[str, dict[str, Any]], config: dict[str, Any]) -> None:
    """Validates configuration against given schema."""
    errors = []
    for key, value in config.items():
        if key not in schema:
            errors.append(f"Unknown configuration parameter: {key}")
            continue

        expected_type = schema[key]["type"]
        if not isinstance(value, expected_type):
            errors.append(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
            continue

        allowed_range = schema[key].get("range")
        if allowed_range and not (allowed_range[0] <= value <= allowed_range[1]):
            errors.append(f"Value out of range for {key}: expected {allowed_range}, got {value}")
            continue

        allowed_values = schema[key].get("allowed")
        if allowed_values and value not in allowed_values:
            errors.append(f"Invalid value for {key}: expected one of {allowed_values}, got {value}")
            continue

    if errors:
        raise KafkaClientBootstrapException("Configuration validation errors: " + "; ".join(errors))


def validate_common_config(config: dict[str, Any]) -> None:
    """Validates common (C/P = *) configuration options for KafkaProducer and KafkaConsumer.

    :param config: Configuration dictionary
    :raises KafkaClientBootstrapException: If configuration is invalid
    """

    if "bootstrap.servers" not in config:
        raise KafkaClientBootstrapException("Configuration validation errors: bootstrap.servers is required")
    if "log_cb" in config:
        raise KafkaClientBootstrapException(
            "In the Python client, the `logger` configuration property is used for log handler, not `log_cb`."
        )
    config.pop("logger", None)

    _validate_against_schema(common_config_schema, config)


def validate_producer_config(config) -> None:
    """Validates producer's (C/P = P) configuration options for KafkaProducer.

    :param config: Configuration dictionary
    :raises KafkaClientBootstrapException: If configuration is invalid
    """

    # Idempotence-related configuration validation
    enable_idempotence = config.get("enable.idempotence", False)
    max_inflight_requests_per_connection = config.pop("max.in.flight.requests.per.connection", None)
    queuing_strategy = config.get("queuing.strategy")
    message_send_max_retries = config.get("retries", config.get("message.send.max.retries"))
    request_required_acks = config.get("acks", config.get("request.required.acks"))
    if request_required_acks == "all":  # all -> -1
        config["acks"] = -1
        config["request.required.acks"] = -1
        request_required_acks = -1

    # Transaction-related configuration validation
    transactional_id = config.get("transactional.id")
    transaction_ms = config.get("transaction.timeout.ms")

    _validate_against_schema(producer_config_schema, config)

    if enable_idempotence:
        if max_inflight_requests_per_connection is not None and max_inflight_requests_per_connection > 5:
            raise KafkaClientBootstrapException(
                "Configuration validation errors: max.in.flight.requests.per.connection "
                "must be 5 (or less) when enable.idempotence is enabled"
            )
        if queuing_strategy is not None and queuing_strategy != "fifo":
            raise KafkaClientBootstrapException(
                "Configuration validation errors: queuing.strategy must be 'fifo' when enable.idempotence is enabled"
            )
        if message_send_max_retries is not None and message_send_max_retries == 0:
            raise KafkaClientBootstrapException(
                "Configuration validation errors: retries must be 0 when enable.idempotence is enabled"
            )
        if request_required_acks is not None and request_required_acks != -1:
            raise KafkaClientBootstrapException(
                "Configuration validation errors: acks must be -1 (all) when enable.idempotence is enabled"
            )

    if transactional_id and not enable_idempotence:
        raise KafkaClientBootstrapException(
            "Configuration validation errors: transactional.id requires enable.idempotence"
        )
    if transaction_ms and not transactional_id:
        raise KafkaClientBootstrapException(
            "Configuration validation errors: transaction.timeout.ms requires transactional.id"
        )


def validate_consumer_config(config) -> None:
    """Validates consumer's (C/P = C) configuration options for KafkaConsumer.

    :param config: Configuration dictionary
    :raises KafkaClientBootstrapException: If configuration is invalid
    """
    # Check for required group.id for most use cases
    if "group.id" not in config:
        raise KafkaClientBootstrapException("Configuration validation errors: group.id is required for KConsumer")

    # Auto-commit related checks
    enable_auto_commit = config.get("enable.auto.commit", True)
    auto_commit_interval_ms = config.get("auto.commit.interval.ms", 5000)
    enable_auto_offset_store = config.get("enable.auto.offset.store", True)

    # Validate auto_commit_interval_ms when auto commit is enabled
    if enable_auto_commit:
        # Check if auto_commit_interval_ms is an int and is positive
        if not isinstance(auto_commit_interval_ms, int) or auto_commit_interval_ms <= 0:
            raise KafkaClientBootstrapException(
                "Configuration validation errors: auto.commit.interval.ms must be a positive integer when enable.auto.commit is True"
            )

    # Validate combination of auto offset store and auto commit
    if not enable_auto_offset_store and not enable_auto_commit:
        # This is allowed but requires explicit calls to store_offsets() and commit()
        pass

    _validate_against_schema(consumer_config_schema, config)


def validate_config(config_type: Literal["common", "producer", "consumer"], config: dict[str, Any]) -> None:
    """
    Validates configuration options for KafkaProducer and KafkaConsumer. Each configuration type has its own schema
    and each key in the configuration dictionary MUST belong to a valid schema.

    :param config_type: Configuration type
    :param config: Configuration dictionary
    :raises KafkaClientBootstrapException: If configuration is invalid
    """

    if config_type == "common":
        validate_common_config(config)
    elif config_type == "producer":
        producer_only_config = {**config}
        rest_config = {}

        for key in common_config_schema.keys():
            value = producer_only_config.pop(key, None)
            if value is not None:
                rest_config[key] = value
        validate_producer_config(producer_only_config)
        validate_common_config(rest_config)
    elif config_type == "consumer":
        consumer_only_config = {**config}
        rest_config = {}

        for key in common_config_schema.keys():
            value = consumer_only_config.pop(key, None)
            if value is not None:
                rest_config[key] = value
        validate_consumer_config(consumer_only_config)
        validate_common_config(rest_config)
    else:
        raise ValueError("Invalid configuration type")

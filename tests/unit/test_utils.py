from random import choice as random_choice
from typing import Any, Literal

import pytest

from kafka_mocha.exceptions import KafkaClientBootstrapException
from kafka_mocha.utils import (
    common_config_schema,
    consumer_config_schema,
    producer_config_schema,
    validate_common_config,
    validate_config,
    validate_consumer_config,
    validate_producer_config,
)

valid_common_string_fields = {
    "builtin.features": "gzip",
    "client.id": "test-client",
    "bootstrap.servers": "localhost:9092",
    "metadata.broker.list": "localhost:9092",
    "topic.blacklist": "blacklisted-topic",
    "debug": "all",
    "broker.address.family": "any",
    "broker.version.fallback": "2.7.0",
    "security.protocol": "plaintext",
}


def valid_config_factory(config_type: Literal["common", "producer", "consumer"]) -> list[tuple[str, Any]]:
    """Factory function for generating valid configuration parameters for given client type."""
    if config_type == "common":
        schema = common_config_schema
    elif config_type == "producer":
        schema = producer_config_schema
    else:
        schema = consumer_config_schema

    valid_common_config = []
    for key, value in schema.items():
        if value["type"] is str:
            if value["allowed"] is None:
                valid_common_config.append((key, valid_common_string_fields.get(key, "dummy")))
            else:
                valid_common_config.append((key, random_choice(value["allowed"])))
        elif value["type"] is int:
            valid_common_config.append((key, int((value["range"][0] + value["range"][1]) / 2)))
        elif value["type"] is bool:
            valid_common_config.append((key, random_choice([True, False])))
        else:
            raise ValueError(f"Invalid type: {value[type]}")
    return valid_common_config


def invalid_config_factory(config_type: Literal["common", "producer", "consumer"]) -> list[tuple[str, Any]]:
    """Factory function for generating invalid configuration parameters for given client type."""
    if config_type == "common":
        schema = common_config_schema
    elif config_type == "producer":
        schema = producer_config_schema
    else:
        schema = consumer_config_schema

    invalid_config = []
    for key, value in schema.items():
        if value["type"] is str:
            if value["allowed"] is None:
                invalid_config.append((key, 123))
            else:
                invalid_config.append((key, "dummy"))
        elif value["type"] is int:
            invalid_config.append((key, "test"))
        elif value["type"] is bool:
            invalid_config.append((key, 123))
        else:
            raise ValueError(f"Invalid type: {value[type]}")
    return invalid_config


@pytest.mark.parametrize("key, value", valid_config_factory("common"))
def test_validate_common_config_happy_path(key: str, value: Any) -> None:
    """Test validate_common_config with valid configuration parameters."""

    config = {"bootstrap.servers": "localhost:9092", key: value} if key != "bootstrap.servers" else {key: value}
    validate_common_config(config)


@pytest.mark.parametrize("key, value", invalid_config_factory("common"))
def test_validate_common_config_unhappy_path(key: str, value: Any) -> None:
    """Test validate_common_config with invalid configuration parameters."""

    config = {"bootstrap.servers": "localhost:9092", key: value} if key != "bootstrap.servers" else {key: value}
    with pytest.raises(KafkaClientBootstrapException):
        validate_common_config(config)


def test_validate_common_config_required_fields() -> None:
    """Test validate_common_config with missing required configuration parameters."""

    config = {**valid_common_string_fields}
    del config["bootstrap.servers"]
    with pytest.raises(KafkaClientBootstrapException):
        validate_common_config(config)


@pytest.mark.parametrize("key, value", valid_config_factory("producer"))
def test_validate_producer_config_happy_path(key: str, value: Any) -> None:
    """Test validate_common_config with valid configuration parameters."""

    config = {key: value}
    validate_producer_config(config)


@pytest.mark.parametrize("key, value", invalid_config_factory("producer"))
def test_validate_producer_config_unhappy_path(key: str, value: Any) -> None:
    """Test validate_producer_config with invalid configuration parameters."""

    config = {key: value}
    with pytest.raises(KafkaClientBootstrapException):
        validate_producer_config(config)


@pytest.mark.parametrize("key, value", valid_config_factory("consumer"))
def test_validate_consumer_config_happy_path(key: str, value: Any) -> None:
    """Test validate_consumer_config with valid configuration parameters."""

    config = {key: value}
    validate_consumer_config(config)


@pytest.mark.parametrize("key, value", invalid_config_factory("consumer"))
def test_validate_consumer_config_unhappy_path(key: str, value: Any) -> None:
    """Test validate_consumer_config with invalid configuration parameters."""

    config = {key: value}
    with pytest.raises(KafkaClientBootstrapException):
        validate_consumer_config(config)


def test_validate_config_strategy_producer() -> None:
    """Test validate_config with producer configuration parameters."""

    validate_config("producer", {**valid_common_string_fields, "acks": 1, "transactional.id": "test-transactional-id"})
    with pytest.raises(KafkaClientBootstrapException):
        validate_config(
            "common", {**valid_common_string_fields, "acks": 1, "transactional.id": "test-transactional-id"}
        )


def test_validate_config_strategy_consumer() -> None:
    """Test validate_config with consumer configuration parameters."""

    validate_config("consumer", {**valid_common_string_fields, "group.id": "test-group-id"})
    with pytest.raises(KafkaClientBootstrapException):
        validate_config("common", {**valid_common_string_fields, "group.id": "test-group-id"})

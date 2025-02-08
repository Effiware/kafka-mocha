from logging import LogRecord

import pytest

from kafka_mocha.klogger import get_filter, get_custom_logger


def test_all_filter(foo_log_record: LogRecord) -> None:
    """Test that `all` filter passes logs from any module."""
    _filter = get_filter("all")

    for module in ["kafka_simulator", "kproducer", "kconsumer", "foo"]:
        foo_log_record.module = module
        assert _filter(foo_log_record) == True


def test_kafka_only_filter(foo_log_record: LogRecord) -> None:
    """Test that `kafka-only` filter passes logs only from `kafka_simulator` module."""
    _filter = get_filter("kafka-only")

    for module in ["kproducer", "kconsumer", "foo"]:
        foo_log_record.module = module
        assert _filter(foo_log_record) == False

    foo_log_record.module = "kafka_simulator"
    assert _filter(foo_log_record) == True


def test_missing_filter(foo_log_record: LogRecord) -> None:
    """Test that ValueError is raised when unknown filter strategy is requested."""

    with pytest.raises(ValueError):
        _filter = get_filter("missing")


def test_getting_custom_logger() -> None:
    _logger = get_custom_logger("CRITICAL", "test_logger")

    assert _logger.level == 50
    assert _logger.name == "test_logger"
    assert _logger.hasHandlers() == True

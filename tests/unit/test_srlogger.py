from kafka_mocha.schema_registry.srlogger import get_custom_logger


def test_getting_custom_logger() -> None:
    _logger = get_custom_logger("CRITICAL", "test_logger")
    _logger = get_custom_logger("DEBUG", "test_logger")

    assert _logger.level == 10
    assert _logger.name == "test_logger"
    assert _logger.hasHandlers() == True

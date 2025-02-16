import logging
from collections.abc import Callable
from typing import Any, Literal


def get_filter(strategy: Literal["all", "kafka-only"]) -> Callable[[Any], bool]:
    """Factory function for creating log record filters."""
    match strategy:
        case "all":

            def _filter(_) -> bool:
                return True

        case "kafka-only":

            def _filter(record: Any) -> bool:
                return record.module == "kafka_simulator"

        case _:
            raise ValueError(f"Unknown filter strategy {strategy}")
    return _filter


def get_custom_logger(
    loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "ERROR", name="kafka_mocha"
) -> logging.Logger:
    """Initializes (if not already done) and returns a custom logger."""
    logger = logging.getLogger(name)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)-8s %(module)-15s > %(message)s"))

    if not logger.hasHandlers():
        logger.addHandler(stream_handler)
        logger.setLevel(logging.getLevelName(loglevel))
        logger.addFilter(get_filter("all"))
    elif logger.level != logging.getLevelName(loglevel):
        logger.setLevel(logging.getLevelName(loglevel))

    return logger

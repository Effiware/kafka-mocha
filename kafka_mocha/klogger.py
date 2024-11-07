import logging
from collections.abc import Callable
from typing import Literal, Any


def get_filter(strategy: Literal["all", "kafka-only"]) -> Callable[[Any], bool]:
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


def get_custom_logger(name="kafka_mocha"):
    logger = logging.getLogger(name)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("(levelname)-8s %(module)-15s > %(message)s"))

    if not logger.hasHandlers():
        logger.addHandler(stream_handler)
        logger.setLevel(logging.INFO)
        logger.addFilter(get_filter("all"))

    return logger

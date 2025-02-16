import logging
from typing import Literal


def get_custom_logger(
    loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "ERROR", name="schema_registry"
) -> logging.Logger:
    """Initializes (if not already done) and returns a custom logger."""
    logger = logging.getLogger(name)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)-8s schema_registry > %(message)s"))

    if not logger.hasHandlers():
        logger.addHandler(stream_handler)
        logger.setLevel(logging.getLevelName(loglevel))
    elif logger.level != logging.getLevelName(loglevel):
        logger.setLevel(logging.getLevelName(loglevel))

    return logger

from functools import partial, wraps
from typing import Literal, Optional
from unittest.mock import patch

from kafka_mocha.kproducer import KProducer


class mock_producer:
    """Context manager/decorator for mocking confluent_kafka.Producer.

    TODO: More detailed description will be added in the future.
    """

    def __init__(
        self,
        output: Optional[Literal["html", "csv"]] = None,
        loglevel: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    ):
        self._patcher = (
            patch("confluent_kafka.Producer", new=partial(KProducer, output=output, loglevel=loglevel))
            if loglevel
            else patch("confluent_kafka.Producer", new=partial(KProducer, output=output))
        )

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._patcher:
                return func(*args, **kwargs)

        return wrapper

    def __enter__(self):
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._patcher.stop()


class mock_consumer:
    """Context manager/decorator for mocking confluent_kafka.Consumer.

    TODO: More detailed description will be added in the future.
    """

    def __init__(self, loglevel: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None):
        raise NotImplementedError("Not implemented yet")

    def __call__(self, func):
        raise NotImplementedError("Not implemented yet")

    def __enter__(self):
        raise NotImplementedError("Not implemented yet")

    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError("Not implemented yet")

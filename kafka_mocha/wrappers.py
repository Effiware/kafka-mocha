from functools import partial, wraps
from typing import Any, Optional
from unittest.mock import patch

from kafka_mocha.core.kconsumer import KConsumer
from kafka_mocha.core.kproducer import KProducer
from kafka_mocha.models.ktypes import InputFormat, LogLevelType


class mock_producer:
    """Context manager/decorator for mocking confluent_kafka.Producer.

    TODO: More detailed description will be added in the future.
    """

    def __init__(self, output: Optional[dict[str, Any]] = None, loglevel: Optional[LogLevelType] = None):
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

    def __init__(self, inputs: Optional[list[InputFormat]] = None, loglevel: Optional[LogLevelType] = None):
        self._patcher = (
            patch("confluent_kafka.Consumer", new=partial(KConsumer, inputs=inputs, loglevel=loglevel))
            if loglevel
            else patch("confluent_kafka.Consumer", new=partial(KConsumer, inputs=inputs))
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

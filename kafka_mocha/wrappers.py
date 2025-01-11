from functools import wraps
from unittest.mock import patch

from kafka_mocha.kproducer import KProducer

# def mock_producer(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         with patch("confluent_kafka.Producer", new=KProducer):
#             reload(confluent_kafka)
#             return func(*args, **kwargs)
#
#     return wrapper


class mock_producer:
    def __init__(self):
        self._patcher = patch("confluent_kafka.Producer", new=KProducer)

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._patcher as foo:
                return func(*args, **kwargs)

        return wrapper

    def __enter__(self):
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._patcher.stop()

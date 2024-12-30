import inspect
from functools import wraps
from unittest.mock import patch

import confluent_kafka
import sys

from kafka_mocha.kproducer import KProducer
from importlib import reload
# from confluent_kafka import Producer as ConfluentProducer

# def mock_producer(cls):
#     """Wrapp Kafka Producer class and return KProducer (mock)
#
#     :param cls:
#     :return:
#     """
#
#     @wraps(cls)
#     def wrapper(*args, **kwargs):
#         return KProducer(*args, **kwargs)
#
#     return wrapper

# def mock_producer(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         original_producer = ConfluentProducer
#         try:
#             ConfluentProducer = KProducer
#             return func(*args, **kwargs)
#         finally:
#             ConfluentProducer = original_producer
#     return wrapper


def mock_producer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with patch("confluent_kafka.Producer", new=KProducer):
            reload(confluent_kafka)
            return func(*args, **kwargs)

    return wrapper


# class MockProducer:
#     def __init__(self):
#         # self._original_producer = ConfluentProducer
#         # self._patcher = patch("confluent_kafka.Producer", new=KProducer)
#         self._patcher = patch(ConfluentProducer.__module__, new=KProducer)
#         self._patcher = patch(inspect.getmodule(ConfluentProducer), new=KProducer)
#
#     def __call__(self, func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             with self._patcher:
#                 return func(*args, **kwargs)
#         return wrapper
#
#     def __enter__(self):
#         self._patcher.start()
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self._patcher.stop()

class MockProducer:
    def __init__(self):
        self._patcher = patch("confluent_kafka.Producer", new=KProducer)


    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._patcher:
                # reload(confluent_kafka)
                return func(*args, **kwargs)
        return wrapper

    def __enter__(self):
        self._patcher.start()
        # reload(confluent_kafka)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._patcher.stop()
        # reload(confluent_kafka)
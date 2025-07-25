from functools import partial, wraps
from typing import Optional
from unittest.mock import patch

from kafka_mocha.models.ktypes import LogLevelType
from kafka_mocha.schema_registry.mock_schema_registry_client import MockSchemaRegistryClient


class mock_schema_registry:
    """Context manager/decorator for mocking confluent_kafka.schema_registry.SchemaRegistryClient.

    TODO: More detailed description will be added in the future.
    """

    def __init__(self, register_schemas: Optional[list[dict]] = None, loglevel: Optional[LogLevelType] = None):
        self._patcher = (
            patch(
                "confluent_kafka.schema_registry.SchemaRegistryClient",
                new=partial(MockSchemaRegistryClient, register_schemas=register_schemas, loglevel=loglevel),
            )
            if loglevel
            else patch(
                "confluent_kafka.schema_registry.SchemaRegistryClient",
                new=partial(MockSchemaRegistryClient, register_schemas=register_schemas),
            )
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

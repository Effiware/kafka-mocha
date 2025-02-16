import pytest

from kafka_mocha.schema_registry import mock_schema_registry
from kafka_mocha.schema_registry.mock_schema_registry_client import MockSchemaRegistryClient


@pytest.hookimpl(tryfirst=True)
def test_schema_registry_bootstrap() -> None:
    """Test that Schema Registry Mock is bootstrapped correctly."""
    assert MockSchemaRegistryClient._instance is None


@pytest.hookimpl(tryfirst=True)
def test_schema_registry_is_singleton() -> None:
    """Test that Schema Registry Mock is actually a singleton."""
    schema_registry_1 = MockSchemaRegistryClient({"url": "http://localhost:8081"})
    schema_registry_2 = MockSchemaRegistryClient({"url": "http://localhost:8082"})

    assert schema_registry_1._instance is schema_registry_2._instance
    assert schema_registry_1 is schema_registry_2

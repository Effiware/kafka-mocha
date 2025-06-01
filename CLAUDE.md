# Project Notes for Claude

This file contains notes about the project to help Claude Code provide better assistance.

## Project Type
Python library for mocking Kafka components (KafkaSimulator, KProducer, KConsumer, MockSchemaRegistry)

## Language & Framework
- **Language**: Python
- **Testing Framework**: pytest
- **Package Manager**: Poetry

## Project Structure
- `kafka_mocha/`: Main library source code
  - `kafka_simulator.py`: Core Kafka simulation engine
  - `kproducer.py`: Mock Kafka producer
  - `kconsumer.py`: Mock Kafka consumer
  - `schema_registry/`: Mock Schema Registry implementation
- `tests/`: Test directory
  - `unit/`: Unit tests
  - `integration/`: Integration tests
- `examples/`: Example usage of the library (also: doctests)

## Common Commands
- **Run Tests**: `poetry run pytest`
- **Run Specific Test**: `poetry run pytest tests/path/to/test_file.py::test_function`
- **Run Tests with Coverage**: `poetry run pytest --cov=kafka_mocha`

## Notable Features
1. Mock implementation of Kafka components for testing
2. Support for transaction coordination
3. Schema Registry mocking
4. Support for producer and consumer APIs that match confluent_kafka

## Development Notes
- Always invoke tests using poetry, e.g. `poetry run pytest`
- All tests should be run using Poetry (`poetry run pytest`) to ensure the correct environment is used.
- The KConsumer implementation supports consumer groups, subscription, offset tracking, and poll/consume operations.
- The Kafka simulation is maintained by KafkaSimulator which is a singleton.
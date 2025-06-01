# Embedded Kafka (Kafka Simulator) for Python

[![PyPI](https://img.shields.io/pypi/v/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - License](https://img.shields.io/pypi/l/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Coverage](https://img.shields.io/badge/coverage-93%25-gree)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Implementation](https://img.shields.io/pypi/implementation/kafka_mocha)](https://pypi.org/project/kafka-mocha/)

Embedded Kafka is a mocking library for the `confluent_kafka` library used for Apache Kafka. Its goal is to ease the
effort
of writing integration tests that utilize `Producer` and/or `Consumer` instances. Of course, you can always span your
own
Kafka Cluster just for testing purposes, but it is not always the best solution.

With **kafka_mocha** you no longer need to have a Kafka Cluster running to test your Kafka-related code. Instead, you
can use the `KProducer`and `KConsumer` (by simply decorating your code with `@mock_producer`/`@mock_consumer`) and check
the behavior of your
code - or even the messages that are being produced and consumed in the browser!

Inspiration for this project comes from the [moto](https://pypi.org/project/moto/) library, which provides a similar
feature for AWS SDK.

## Support me with

[<img alt="Buy Me A Coffee" height="40" src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"/>](https://buymeacoffee.com/and.ratajski)

## Project Overview

The main component of this project is a process called `KafkaSimulator` which simulates the behavior of an actual Kafka
Cluster, within the bounds of implementation limitations. The current version includes a `KProducer` class that acts as
a mock for the `Producer` from the `confluent_kafka` package, and a `KConsumer` class that acts as a mock for the
`Consumer` from the same package. Both classes can be used as decorators to mock the behavior of the respective
classes in your tests, allowing you to produce and consume messages without the need for a real Kafka Cluster.

Behavior replication is quite advanced, including support for transactions, manual management of offsets, flushes,
subscriptions, and more. The `KProducer` and `KConsumer` classes can be used in a similar way to the original
`Producer` and `Consumer` classes, allowing you to write tests that closely resemble your production code.

Additionally, the project includes a `SchemaRegistryMock` class that acts as a mock for the `SchemaRegistryClient` from
the `confluent_kafka` package. It allows you to register and retrieve schemas, as well as serialize and deserialize
messages using AVRO and JSON serialization. This is particularly useful when working with production code.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
    - [Starting Kafka Simulator](#starting-kafka-simulator)
    - [KProducer](#kproducer)
    - [KConsumer](#kconsumer)
    - [Schema Registry Mock](#schema-registry-mock)
    - [Check out the examples](#check-out-the-examples)
    - [Absolute imports](#absolute-imports)
- [Contributing](#contributing)
- [License](#license)

## Installation

<details>
<summary><b>Official Release</b></summary>

```sh
pip install kafka_mocha
```

or using your favorite package manager, e.g. [poetry](https://python-poetry.org/):

```sh
poetry add kafka_mocha
```

</details>
</br>

<details>
<summary>Prerelease or Development Version</summary>

From GitHub (development version):

```sh
pip install git+https://github.com/Effiware/kafka-mocha@develop
```

or as published (prerelease) version:

```sh
poetry add kafka_mocha --allow-prereleases
```

</details>

## Usage

### Starting Kafka Simulator

Kafka Simulator is automatically ran whenever any instance of either `KProdcer` or `KConsumer` is created (e.g. via
`mock_producer`, `mock_consumer`). So there is no need to manually start it.

Upon default logging settings a custom start-up messages might be visible (default logging level is set to WARNING
though):

```text
INFO     ticking_thread  > Buffer for KProducer(4409519920): ticking initialized
INFO     buffer_handler  > Buffer for KProducer(4409519920) has been primed, length: 5, timeout: 300
INFO     kafka_simulator > Handle producers has been primed
INFO     kafka_simulator > Kafka Simulator initialized, id: 4399382400
DEBUG    kafka_simulator > Registered topics: [KTopic(name='_schemas', partition_no=1, config=None), KTopic(name='__consumer_offsets', partition_no=1, config=None)]
INFO     ticking_thread  > Buffer for KProducer(4409519920): ticking started
DEBUG    kproducer       > KProducer(4409519920): received ack: BUFFERED
DEBUG    buffer_handler  > Buffer for KProducer(4409519920): received done (or manual flush) signal...
DEBUG    kafka_simulator > Appended message: (partition=0, offset=1000, key=b'4df33f7a-fcee-4b3b-b176-a4e650540401', value=b'\x00\x00\x00\x00\x01H4df33f7a-fcee-4b3b-b176-a4e650540401\x08John\x06Doe\x01\x04\xbe\xfd\x83\x8b\xa2e\x00\x00\x00\x00\x00\x00\x00\x00He5df0ed3-765c-4f58-b18c-aea4400dfce4\xbe\xfd\x83\x8b\xa2e(kafka_mocha_examples\n1.0.0', headers=[]))
INFO     buffer_handler  > Buffer for KProducer(4409519920): Kafka response: SUCCESS
INFO     ticking_thread  > Buffer for KProducer(4409519920): stop event
DEBUG    buffer_handler  > Buffer for KProducer(4409519920): received done (or manual flush) signal...
INFO     buffer_handler  > Buffer for KProducer(4409519920): nothing to send...
```

Additionally, all the messages produced by the `KProducer` instances are stored in the `KafkaSimulator` instance. The
messages can be dropped to either HTML or CSV file by passing `output` parameter, see `KProucer`
and [outputs](./examples/outputs) for more details.

### KProducer

To use the `KProducer` class in your tests, you need to import it from the `kafka_simulator` package:

```python
import confluent_kafka

from kafka_mocha import mock_producer


@mock_producer()
def handle_produce():
    """Most basic usage of the KProducer class. For more go to `examples` directory."""
    producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})
    producer.produce("test-topic", "some value".encode(), "key".encode())
    producer.flush()
```

The `KProducer` class replicates (pretty well IMHO) the interface and behavior of the `Producer` class from the
`confluent_kafka` library. For more examples, see the [examples](./examples) directory.

For the time being, the `KProducer` is not fully thread-safe, so it is recommended to use it in a single-threaded,
single-process environment. Issue is being discussed in GitHub Issues.

<details>
<summary>Parameters for mock_producer</summary>

| No | Parameter name                 | Parameter type   | Comment                                                       |
|----|--------------------------------|------------------|---------------------------------------------------------------|
| 1  | loglevel                       | OptionalLiteral] | See available levels in `logging` library                     |
| 2  | output                         | Optional[dict]   | Dictionary with output configuration                          |
| 3  | output.format                  | Literal          | `html`, `csv` or `int` - output format of messages emitted    |
| 4  | output.name                    | str              | Name of the output file (only for HTML), e.g. kafka-dump.html |
| 5  | output.include_internal_topics | Optional[bool]   | Flag to include internal topics in the output                 |
| 6  | output.include_markers         | Optional[bool]   | Flag to include transaction markers in the output             |

</details>

### KConsumer

To use the `KConsumer` class in your tests, you need to import it from the `kafka_simulator` package:

```python
import confluent_kafka

from kafka_mocha import mock_consumer


@mock_consumer()
def consume_preloaded_messages_batched():
    """Most basic usage of the KConsumer class. For more go to `examples` directory."""
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group-consume",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe(["some-topic", "another-topic"])
    msgs = consumer.consume(10, timeout=0.5)
    for msg in msgs:
        if msg.error():
            raise confluent_kafka.KafkaException(msg.error())
        else:
            print(f"Consumed message: {{'key': '{msg.key()}', 'value': '{msg.value(None)}...'}}")
    consumer.close()
```

The `KConsumer` class replicates (pretty well IMHO) the interface and behavior of the `KConsumer` class from the
`confluent_kafka` library. For more examples, see the [examples](./examples) directory.

For the time being, the `KProducer` is not fully thread-safe, so it is recommended to use it in a single-threaded,
single-process environment. Issue is being discussed in GitHub Issues.

<details>
<summary>Parameters for mock_consumer</summary>

| No | Parameter name              | Parameter type       | Comment                                                                                        |
|----|-----------------------------|----------------------|------------------------------------------------------------------------------------------------|
| 1  | loglevel                    | Optional[Literal]    | See available levels in `logging` library                                                      |
| 2  | inputs                      | Optional[list[dict]] | List of dictionary with inputs configuration                                                   |
| 3  | input                       | dict                 | Configuration of an input                                                                      |
| 4  | input.source                | str                  | Path to a JSON file with input data (see example structure)                                    |
| 5  | input.topic                 | str                  | Topic name to which the input data should be sent                                              |
| 6  | input.subject_name_strategy | Optional[Literal]    | Name strategy for subject, one of `["topic", "topic_record", "record"]` - `"topic"` by default |
| 7  | input.serialize             | Optional[bool]       | A flag used to serialize data, False by default                                                |

</details>

### Schema Registry Mock

The Schema Registry mock is a part of the `kafka_mocha` package. It is heavily inspired by the
[confluent-kafka-python/mock_schema_registry_client](https://github.com/confluentinc/confluent-kafka-python/blob/master/src/confluent_kafka/schema_registry/mock_schema_registry_client.py)
implementation and hence is licensed under the Apache License, Version 2.0.

It provides fully compatible implementation of the `SchemaRegistryClient` class from the `confluent_kafka` library and
similarly to the `KProducer` class, it can be used as a decorator:

```python
import confluent_kafka.schema_registry
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

from kafka_mocha.schema_registry import mock_schema_registry


@mock_schema_registry()
def quick_start():
    """Most basic usage of the MockSchemaRegistry class. For more go to `examples` directory."""
    schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})
    avro_serializer = AvroSerializer(schema_registry, conf={"auto.register.schemas": False})
    avro_serializer({"foo": "bar"}, SerializationContext("topic", MessageField.VALUE))
```

For more examples, see the [examples](./examples) directory.

<details>
<summary>Parameters for mock_schema_registry</summary>

| No | Parameter name   | Parameter type       | Comment                                                                           |
|----|------------------|----------------------|-----------------------------------------------------------------------------------|
| 1  | loglevel         | Optional[Literal]    | See available levels in `logging` library                                         |
| 2  | register_schemas | Optional[list[dict]] | List of schemas to load into Schema Registry Mock on launch                       |
| 3  | schema.source    | str                  | Path (relative) to a file with schema definition - only .avsc and .json supported |
| 4  | schema.subject   | Optional[str]        | Subject Name under which register the schema, 'file_name' + '-value' by default   |

</details>

## Check out the examples

It is highly recommended to check out the [examples](./examples) directory, which contains various examples of how to
use the `KProducer`, `KConsumer`, and `SchemaRegistryMock` classes. The examples cover a wide range of use cases,
from the most basic ones to more advanced scenarios, including transactions, manual management of offsets, and
schema registration. The examples are designed to be easy to understand and can be used as a starting point for your
tests. They also demonstrate how to use the `mock_producer`, `mock_consumer`, and `mock_schema_registry` decorators to
mock the behavior of the respective classes in your tests.

## Absolute imports

Due to specific nature of python imports, it is recommended (**and enforced**) to use absolute imports in your code.
This is especially
important when using `mock_producer` and `mock_consumer` decorators, as they are using patching mechanism from
`unittest.mock` module.

Imports that will work:

```python
# USE THAT
import confluent_kafka
import confluent_kafka.schema_registry

producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})  # OK
schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})  # OK
```

Imports that will not work:

```python
# DON'T USE THAT
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient

producer = Producer({"bootstrap.servers": "localhost:9092"})  # Will not work
schema_registry = SchemaRegistryClient({"url": "http://localhost:8081"})  # Will not work
```

## Contributing

We welcome contributions! Before posting your first PR, please see our [contributing guidelines](CONTRIBUTING.md) for
more details.

Also, bear in mind that this project uses [Poetry](https://python-poetry.org/) for dependency management. If you are not
familiar with it,
please first read the [Poetry documentation](https://python-poetry.org/docs/) and:

1. Setup poetry environment (recommended)
2. Don't overwrite the `pyproject.toml` file manually (Poetry will do it for you)
3. Don't recreate the `poetry.lock` (unless you know what you are doing)

<details>
<summary>Cloning the repository</summary>

```sh
git clone git@github.com:Effiware/kafka-mocha.git
cd kafka-mocha
```

</details>
</br>

<details>
<summary>Installing dependencies</summary>

Default (and recommended) way:

```shell
poetry install --with test
```

Standard way:

```sh
poetry export -f requirements.txt --output requirements.txt
pip install -r requirements.txt
```

</details>
</br>

<details>
<summary>Running tests</summary>

Currently, test configuration is set up to run with `pytest` and kept in [pytest.ini](./tests/pytest.ini) file. You can
run them with:

```sh
poetry run pytest
```

</details>

## License

This project is primarily licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Parts of this project (specifically the Schema Registry mock implementation) contain code from Confluent Inc.,
licensed under the Apache License, Version 2.0. See [LICENSE.APACHE](LICENSE.APACHE) for details.

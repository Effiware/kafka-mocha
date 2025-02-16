# Embedded Kafka (Kafka Simulator) for Python

[![PyPI](https://img.shields.io/pypi/v/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - License](https://img.shields.io/pypi/l/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Coverage](https://img.shields.io/badge/coverage-92%25-gree)](https://pypi.org/project/kafka-mocha/)
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
a mock for the `Producer` from the `confluent_kafka` package. A `KConsumer` class is still under development.

Additionally, the project includes a `SchemaRegistryMock` class that acts as a mock for the `SchemaRegistryClient` from
the `confluent_kafka` package.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
    - [Starting Kafka Simulator](#starting-kafka-simulator)
    - [KProducer](#kproducer)
    - [KConsumer](#kconsumer)
    - [Schema Registry Mock](#schema-registry-mock)
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

Upon default logging settings a custom start-up messages might be visible:

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

The `KProducer` class replicates the interface and behavior of the `Producer` class from the `confluent_kafka` library.
For more examples, see the [examples](./examples) directory.

<details>
<summary>Parameters for mock_producer</summary>

| No | Parameter name                 | Parameter type | Comment                                                       |
|----|--------------------------------|----------------|---------------------------------------------------------------|
| 1  | loglevel                       | Literal        | See available levels in `logging` library                     |
| 2  | output                         | dict           | Dictionary with output configuration                          |
| 3  | output.format                  | Literal        | `html`, `csv` or `int` - output format of messages emitted    |
| 4  | output.name                    | str            | Name of the output file (only for HTML), e.g. kafka-dump.html |
| 5  | output.include_internal_topics | bool           | Flag to include internal topics in the output                 |
| 6  | output.include_markers         | bool           | Flag to include transaction markers in the output             |

</details>

### KConsumer

The `KConsumer` class is still under development. It will replicate the interface and behavior of the `Consumer` class
from the `confluent_kafka` library.

<details>
<summary>Parameters for mock_consumer</summary>

| No | Parameter name | Parameter type | Comment                                   |
|----|----------------|----------------|-------------------------------------------|
| 1  | loglevel       | Literal        | See available levels in `logging` library |
| 2  |                |                |                                           |
| 3  |                |                |                                           |

</details>

### Schema Registry Mock

The Schema Registry mock is a part of the `kafla_mocha` package. It is heavily inspired by
the [confluent-kafka-python/mock_schema_registry_client](https://github.com/confluentinc/confluent-kafka-python/blob/master/src/confluent_kafka/schema_registry/mock_schema_registry_client.py)
implementation and hence is lincensed under the Apache License, Version 2.0.

It provides fully compatible implementation of the `SchemaRegistryClient` class from the `confluent_kafka` library and
similarly to the `KProducer` class, it can be used as a decorator:

```python
import confluent_kafka.schema_registry
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

from kafka_mocha.schema_registry import mock_schema_registry


@mock_schema_registry()
def quick_start():
    schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})
    avro_serializer = AvroSerializer(schema_registry, conf={"auto.register.schemas": False})
    avro_serializer({"foo": "bar"}, SerializationContext("topic", MessageField.VALUE))
```

For more examples, see the [examples](./examples) directory.

<details>
<summary>Parameters for mock_schema_registry</summary>

| No | Parameter name   | Parameter type | Comment                                                                         |
|----|------------------|----------------|---------------------------------------------------------------------------------|
| 1  | loglevel         | Literal        | See available levels in `logging` library                                       |
| 2  | register_schemas | list[str]      | List of schemas (as relative paths) to load into Schema Registry Mock on launch |
| 3  |                  |                |                                                                                 |

</details>

## Absolute imports

Due to specific nature of python imports, it is recommended (**and enforced**) to use absolute imports in your code.
This is especially
important when using `mock_producer` and `mock_consumer` decorators, as they are using patching mechanism from
`unittest.mock` module.

Imports that will work:

```python
import confluent_kafka
import confluent_kafka.schema_registry

producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092"})  # OK
schema_registry = confluent_kafka.schema_registry.SchemaRegistryClient({"url": "http://localhost:8081"})  # OK
```

Imports that will not work:

```python
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

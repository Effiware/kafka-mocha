# Embedded Kafka (Kafka Simulator) for Python

[![PyPI](https://img.shields.io/pypi/v/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - License](https://img.shields.io/pypi/l/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Status](https://img.shields.io/pypi/status/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kafka_mocha)](https://pypi.org/project/kafka-mocha/)
[![PyPI - Implementation](https://img.shields.io/pypi/implementation/kafka_mocha)](https://pypi.org/project/kafka-mocha/)

Embedded Kafka is a mocking library for the `confluent_kafka` library used for Apache Kafka. Its goal is to ease the effort 
of writing integration tests that utilize `Producer` and/or `Consumer` instances. Of course, you can always span your own
Kafka Cluster just for testing purposes, but it is not always the best solution.

With **kafka_mocha** you no longer need to have a Kafka Cluster running to test your Kafka-related code. Instead, you can use the `KProducer`
and `KConsumer` (by simply decorating your code with `@mock_producer`/`@mock_consumer`) and check the behavior of your code - or even
the messages that are being produced and consumed in the browser!

Inspiration for this project comes from the [moto](https://pypi.org/project/moto/) library, which provides a similar feature for AWS SDK.


## Project Overview

The main component of this project is a process called `KafkaSimulator` which simulates the behavior of an actual Kafka Cluster,
within the bounds of implementation limitations. The current version includes a `KProducer` class that acts as a mock for the `Producer` 
from the `confluent_kafka` package. A `KConsumer` class is still under development.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Starting Kafka Simulator](#starting-kafka-simulator)
  - [KProducer](#kproducer)
  - [KConsumer](#kconsumer)
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

Kafka Simulator is automatically ran whenever any instance of either `KProdcer` or `KConsumer` is created (e.g. via `mock_producer`,
`mock_consumer`). So there is no need to manually start it.

Upon default logging settings a custom start-up messages might be visible:

```text
INFO     kafka_simulator > Kafka Simulator initialized
INFO     ticking_thread  > Buffer for KProducer(4368687344): ticking initialized
INFO     buffer_handler  > Buffer for KProducer(4368687344) has been primed, size: 300, timeout: 2
INFO     kafka_simulator > Kafka Simulator initialized
INFO     kafka_simulator > Handle producers has been primed
INFO     kafka_simulator > Kafka Simulator initialized
INFO     ticking_thread  > Buffer for KProducer(4368687344): ticking started
```

Additionally, all the messages produced by the `KProducer` instances are stored in the `KafkaSimulator` instance. The messages can be
dropped to either HTML or CSV file by passing `output` parameter, see `KProucer` and [outputs](./examples/outputs) for more details.

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

<details>
<summary>Parameters for mock_producer</summary>

| No | Parameter name | Parameter type | Comment                                              |
|----|----------------|----------------|------------------------------------------------------|
| 1  | loglevel       | Literal        | See available levels in `logging` library            |
| 2  | output         | Literal        | HTML, CSV or INT - output format of messages emitted |
| 3  |                |                |                                                      |

</details>

### KConsumer

The `KConsumer` class is still under development. It will replicate the interface and behavior of the `Consumer` class from the `confluent_kafka` library.

<details>
<summary>Parameters for mock_consumer</summary>

| No | Parameter name | Parameter type | Comment                                   |
|----|----------------|----------------|-------------------------------------------|
| 1  | loglevel       | Literal        | See available levels in `logging` library |
| 2  |                |                |                                           |
| 3  |                |                |                                           |

</details>

## Contributing

We welcome contributions! Before posting your first PR, please see our [contributing guidelines](CONTRIBUTING.md) for more details.

Also, bear in mind that this project uses [Poetry](https://python-poetry.org/) for dependency management. If you are not familiar with it,
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

Currently, test configuration is set up to run with `pytest` and kept in [pytest.ini](./tests/pytest.ini) file. You can run them with:

```sh
poetry run pytest
```

</details>

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

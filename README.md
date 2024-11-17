# Kafka Simulator

Kafka Simulator is a mocking library for the `confluent_kafka` library used for Apache Kafka. This library allows integration tests to utilize `Producer` and `Consumer` instances without an actual connection to a Kafka Cluster. 

## Project Overview

The main component of this project is a process called `KafkaSimulator` which simulates the behavior of an actual Kafka Cluster, within the bounds of implementation limitations. The current version includes a `KProducer` class that acts as a mock for the `Producer` from the `confluent_kafka` package. A `Consumer` class is still under development.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Starting Kafka Simulator](#starting-kafka-simulator)
  - [KProducer](#kproducer)
- [Contributing](#contributing)
- [License](#license)

## Installation

First, clone the repository:

```sh
git clone https://github.com/your-repo/kafka-simulator.git
cd kafka-simulator
```

You can install the necessary dependencies using:

```sh
pip install -r requirements.txt
```

## Usage

### Starting Kafka Simulator

Kafka Simulator is automatically run whenever any instance of `KProdcer` (e.g. via `mock_producer`) is created.
So there is no need to manually start it.

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

### KProducer

To use the `KProducer` class in your tests, you need to import it from the `kafka_simulator` package:

```python
from confluent_kafka import Producer
from kafka_simulator import mock_producer

# Example usage
@mock_producer
def producer_factory(conf):
    return Producer(conf)


producer = producer_factory({'bootstrap.servers': 'localhost:9092'})
producer.produce(topic='test-topic', value='Test message')
producer.flush()
```

The `KProducer` class replicates the interface and behavior of the `Producer` class from the `confluent_kafka` library.

## Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
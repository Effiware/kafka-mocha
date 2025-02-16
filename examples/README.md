# Examples of using the `kafka_mocha` package

## Total isolation

The examples in this directory are designed to be run in total isolation from the Kafka broker (e.g. in a **CI/CD
environment**). They use a test environment, where the Kafka broker is simulated by the `kafka_mocha` package. This
means that you don't need to have a Kafka broker running to run the examples

Moreover, Schema Registry is also simulated by the `kafka_mocha` package, so you don't need to have a Schema Registry
running to run the examples (but you can).

No external calls are made in these examples, so you don't need to have access to the internet to run them.

## Dependencies

Please mind that you need to install all the dependencies (including test ones) before running the examples. You can do
this by running the following command:

```shell
poetry install --with=test
```

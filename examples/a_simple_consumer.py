import doctest


# import confluent_kafka
#
# from kafka_mocha import mock_consumer
# TOPIC_NAME = "test-simple-producer-topic"
#
#
# @mock_producer()
# def invalid_configuration():
#     """Mock producer will always validate the configuration and raise exception in case of:
#         - missing required configuration parameters
#         - unknown configuration parameters
#         - invalid configuration values/types
#
#     >>> invalid_configuration()
#     Traceback (most recent call last):
#     ...
#     kafka_mocha.exceptions.KafkaClientBootstrapException: Configuration validation errors: Value out of range for batch.size: expected (1, 2147483647), got False; Unknown configuration parameter: foo
#     """
#     producer = confluent_kafka.Producer({"bootstrap.servers": "localhost:9092", "batch.size": False, "foo": "bar"})
#
#     # some pre-processing
#     producer.produce(
#         TOPIC_NAME,
#         datetime.now().isoformat(),
#         str(id(producer)),
#         on_delivery=lambda err, msg: print("Will not get here"),
#     )


if __name__ == "__main__":
    # TODO: Implement examples for KConsumer.
    doctest.testmod(verbose=True)
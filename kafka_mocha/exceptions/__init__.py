class KafkaSimulatorBootstrapException(Exception):
    pass


class KafkaSimulatorProcessingException(Exception):
    pass


class KafkaClientBootstrapException(Exception):
    pass


class KProducerProcessingException(Exception):
    pass


class KProducerMaxRetryException(Exception):
    pass


class KProducerTimeoutException(Exception):
    pass


class KConsumerProcessingException(Exception):
    pass


class KConsumerMaxRetryException(Exception):
    pass


class KConsumerTimeoutException(Exception):
    pass


class KConsumerGroupException(Exception):
    pass

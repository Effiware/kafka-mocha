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

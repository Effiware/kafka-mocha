from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.klogger import get_custom_logger

logger = get_custom_logger()


class KTransactionCoordinator:
    def __init__(self):
        # self.transaction_inited = False
        # self.transaction_begun = False
        self.kafka_simulator = KafkaSimulator()

    def init_transaction(self, transaction_id: str) -> None:
        pass

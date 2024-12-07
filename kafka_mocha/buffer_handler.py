from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal, Callable

from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import PMessage
from kafka_mocha.signals import Tick, KSignals

logger = get_custom_logger()


def get_partitioner(
    topics: dict[str, dict], strategy: Literal["default", "round-robin", "uniform-sticky"] = "default"
) -> Callable[[str, bytes], int]:
    """Strategy pattern (as closure) returning requested kafka producer partitioner."""
    last_assigned_partitions = defaultdict(int)

    match strategy:
        case "default":

            def partitioner(topic: str, key: bytes) -> int:
                if topic not in topics:
                    return 0  # assumes that default partition number for newly created topics is 1
                return abs(hash(key)) % topics[topic]["partition_no"]

        case "round-robin":

            def partitioner(topic: str, _) -> int:
                if topic not in topics:
                    return 0
                last_partition = last_assigned_partitions[topic]
                available_partitions = topics[topic]["partition_no"]
                new_partition = 0 if last_partition == available_partitions - 1 else last_partition + 1
                last_assigned_partitions[topic] = new_partition
                return new_partition

        case _:
            raise NotImplemented(f"Custom strategy and/or {strategy} not yet implemented.")
    return partitioner


def buffer_handler(owner: str, buffer: list[PMessage], buffer_size: int, buffer_timeout: int = 2):
    """Start off with 1:1 relation to KProducer or KConsumer.

    Does not support custom timestamps (yet).
    """
    logger.info(f"Buffer for {owner} has been primed, size: {buffer_size}, timeout: {buffer_timeout}")
    buffer_start_time = datetime.now()
    buffer_elapsed_time = 0
    buffer_loop_no = 0
    kafka_simulator = KafkaSimulator()
    partitioner = get_partitioner(
        {topic.name: {"partition_no": topic.partition_no} for topic in kafka_simulator.topics}
    )

    producer_protocol = kafka_simulator.handle_producers()
    producer_protocol.send(KSignals.INIT.value)
    res = KSignals.BUFFERED
    while True:
        while len(buffer) < buffer_size:  # TODO: byte size instead of length
            new_msg: PMessage | int | float = yield res
            if isinstance(new_msg, int) or isinstance(new_msg, float):
                if new_msg == Tick.DONE:
                    logger.info(f"Buffer for {owner}: received done signal, finishing...")
                    break
                else:
                    buffer_elapsed_time += new_msg
                    logger.debug(f"Buffer for {owner}: checking elapsed time: {buffer_elapsed_time}")
                    if buffer_elapsed_time >= buffer_timeout:
                        logger.debug(f"Buffer for {owner}: forcing flush due to timeout...")
                        break
            else:
                new_msg.timestamp = (
                    buffer_start_time + timedelta(milliseconds=buffer_loop_no * buffer_timeout + buffer_elapsed_time)
                ).timestamp()
                new_msg.partition = (
                    partitioner(new_msg.topic, new_msg.key) if new_msg.partition == -1 else new_msg.partition
                )
                buffer.append(new_msg)
                res = KSignals.BUFFERED
        if buffer:
            res = producer_protocol.send(buffer)
            logger.info(f"Buffer for {owner}: Kafka response: {res}")
        else:
            logger.info(f"Buffer for {owner}: nothing to send...")
        if res == KSignals.SUCCESS:
            buffer.clear()
        buffer_elapsed_time = 0
        buffer_loop_no += 1

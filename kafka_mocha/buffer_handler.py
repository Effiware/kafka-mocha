from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Literal

from kafka_mocha.exceptions import KProducerProcessingException
from kafka_mocha.kafka_simulator import KafkaSimulator
from kafka_mocha.klogger import get_custom_logger
from kafka_mocha.models import PMessage
from kafka_mocha.signals import KSignals, Tick

logger = get_custom_logger()


def _get_elapsed_time(
    buffer_start_time: datetime, buffer_loop_no: int, buffer_timeout: int, buffer_elapsed_time: int
) -> float:
    """Calculate elapsed time based on buffer loop number and timeout."""
    return (
        buffer_start_time + timedelta(milliseconds=buffer_loop_no * buffer_timeout + buffer_elapsed_time)
    ).timestamp()


def get_partitioner(
    topics: dict[str, dict], strategy: Literal["default", "round-robin", "uniform-sticky"] = "default"
) -> Callable[[str, bytes], int]:
    """Strategy pattern (as closure) returning requested kafka producer partitioner."""
    last_assigned_partitions = defaultdict(lambda: -1)

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
            raise NotImplementedError(f"Custom strategy and/or {strategy} not yet implemented.")
    return partitioner


def buffer_handler(
    owner: str, buffer: list[PMessage], buffer_size: int, buffer_timeout: int = 2, transact: bool = False
) -> None:
    """Start off with 1:1 relation to KProducer or KConsumer.

    Does not support custom timestamps (yet).
    """
    logger.info(f"Buffer for {owner} has been primed, size: {buffer_size}, timeout: {buffer_timeout}")
    buffer_start_time = datetime.now()
    buffer_elapsed_time = 0
    buffer_loop_no = 0
    transact_cache = defaultdict(list)
    kafka_simulator = KafkaSimulator()
    partitioner = get_partitioner(
        {topic.name: {"partition_no": topic.partition_no} for topic in kafka_simulator.topics}
    )

    kafka_handler = kafka_simulator.producers_handler
    res = KSignals.BUFFERED
    while True:
        while len(buffer) < buffer_size:  # TODO: byte size instead of length
            new_msg: PMessage | int | float = yield res
            if isinstance(new_msg, int) or isinstance(new_msg, float):
                # Float/int = Tick signal received
                if new_msg == Tick.DONE:
                    logger.debug("Buffer for %s: received done (or manual flush) signal...", owner)
                    break
                else:
                    buffer_elapsed_time += new_msg
                    logger.debug("Buffer for %s: checking elapsed time: %.3fs", owner, buffer_elapsed_time)
                    if buffer_elapsed_time >= buffer_timeout:
                        logger.debug("Buffer for %s: forcing flush due to timeout...", owner)
                        break
            elif new_msg.marker:
                # Transaction marker received
                if not transact:
                    raise KProducerProcessingException("Transaction marker received but transaction is not enabled.")
                if buffer:
                    raise KProducerProcessingException("Transaction marker received but buffer is not empty.")
                logger.debug("Buffer for %s: received marker: %s", owner, new_msg.marker)

                markers_buffer = []
                ts = _get_elapsed_time(buffer_start_time, buffer_loop_no, buffer_timeout, buffer_elapsed_time)
                for topic, partitions in transact_cache.items():
                    for partition in partitions:
                        markers_buffer.append(
                            PMessage(topic, partition, new_msg.key, new_msg.value, timestamp=ts, marker=new_msg.marker)
                        )
                kafka_handler.send(markers_buffer)
                transact_cache = dict()
            else:
                # (Normal) PMessage received
                new_msg.timestamp = _get_elapsed_time(
                    buffer_start_time, buffer_loop_no, buffer_timeout, buffer_elapsed_time
                )
                new_msg.partition = (
                    partitioner(new_msg.topic, new_msg.key) if new_msg.partition == -1 else new_msg.partition
                )
                buffer.append(new_msg)
                transact_cache[new_msg.topic].append(new_msg.partition) if transact else None
                res = KSignals.BUFFERED
        if buffer:
            res = kafka_handler.send(buffer)
            logger.info("Buffer for %s: Kafka response: %s", owner, res)
        else:
            logger.info("Buffer for %s: nothing to send...", owner)
        if res == KSignals.SUCCESS:
            try:
                for msg in buffer:
                    msg.on_delivery(None, "TODO: add proper message")  # TODO
            except Exception as e:
                logger.error("Buffer for %s: Error while executing callback: %s", owner, e)
            finally:
                buffer.clear()
        buffer_elapsed_time = 0
        buffer_loop_no += 1

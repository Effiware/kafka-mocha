import logging
from inspect import GEN_SUSPENDED, getgeneratorstate

from kafka_mocha.kmodels import KMessage
from kafka_mocha.kproducer import KProducer


def test_kproducers_buffer_is_primed(kproducer) -> None:
    """Test that Kafka producer buffer is primed after initialization."""
    assert kproducer.buffer is not None
    assert getgeneratorstate(kproducer._buffer_handler) == GEN_SUSPENDED


def test_kproducers_ticking_thread_is_alive(kproducer) -> None:
    """Test that Kafka producer ticking thread is alive after initialization."""
    assert kproducer._ticking_thread.is_alive()


def test_kproducer_warns_when_messages_left_in_buffer_on_termination(caplog) -> None:
    """Test that Kafka producer warns when messages are left in buffer on termination."""
    kproducer = KProducer(
        {"bootstrap.servers": "localhost:9092", "queue.buffering.max.messages": 10000, "linger.ms": 900000}
    )

    kproducer.buffer.append(KMessage("test-topic", 0, b"key", b"value"))
    del kproducer

    with caplog.at_level(logging.WARNING):
        assert "You may have a bug: Producer terminating with 1 messages" in caplog.text, caplog.text


def test_kproducer_implements_len(kproducer) -> None:
    """Test that Kafka producer implements len dunder method."""
    assert len(kproducer) == 0
    kproducer.buffer.append(KMessage("test-topic", 0, b"key", b"value"))
    assert len(kproducer) == 1

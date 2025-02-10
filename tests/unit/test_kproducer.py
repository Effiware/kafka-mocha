from inspect import getgeneratorstate, GEN_SUSPENDED


def test_kproducers_buffer_is_primed(kproducer) -> None:
    """Test that Kafka producer buffer is primed after initialization."""
    assert kproducer.buffer is not None
    assert getgeneratorstate(kproducer._buffer_handler) == GEN_SUSPENDED


def test_kproducers_ticking_thread_is_alive(kproducer) -> None:
    """Test that Kafka producer ticking thread is alive after initialization."""
    assert kproducer._ticking_thread.is_alive()

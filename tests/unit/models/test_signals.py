from typing import Any

import pytest

from kafka_mocha.models.signals import KMarkers, KSignals, Tick


@pytest.mark.parametrize("interval", [0, 0.0, -1, -1.0, "foo"])
def test_ticking_interval(interval: Any) -> None:
    """Test if the tick interval is an unsigned integer."""
    with pytest.raises(ValueError, match="Tick interval must be an unsigned integer."):
        Tick(interval)


def test_ksignal() -> None:
    """Test if the signal is converted to string."""
    signal = KSignals.INIT
    assert str(signal) == "None"


def test_kmarker() -> None:
    """Test if the marker is converted to string."""
    marker = KMarkers.COMMIT
    assert str(marker) == "COMMIT"

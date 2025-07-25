from datetime import datetime
from time import sleep

from confluent_kafka import TIMESTAMP_CREATE_TIME

from kafka_mocha.models.kmodels import KMessage, KTopic
from kafka_mocha.renderers import render_csv, render_html, render_json


def test_render_html() -> None:
    """Test rendering HTML output."""
    topic_1, topic_2 = (
        KTopic("test-html-topic-1"),
        KTopic("test-html-topic-2", partition_no=3),
    )
    _range = 10

    for i in range(_range):
        for t in [topic_1, topic_2]:
            for p_idx, p in enumerate(t.partitions):
                individual = i + _range * p_idx
                p.append(
                    KMessage(
                        topic=t.name,
                        partition=individual % t.partition_no,
                        offset=individual // t.partition_no,
                        key=f"key_{individual}".encode(),
                        value=f"value_{individual}".encode(),
                        timestamp=(
                            int(datetime.now().timestamp() * 1000),
                            TIMESTAMP_CREATE_TIME,
                        ),
                        headers=[("header_key", b"header_value")] if individual % 3 == 0 else None,
                    )
                )
                sleep(0.01)

    for t in [topic_1, topic_2]:
        for p in t.partitions:
            p._heap.sort(key=lambda x: x.timestamp()[1])

    render_html([topic_1, topic_2], name="test-render-html.html")


def test_render_csv() -> None:
    """Test rendering CSV output."""
    topic_1, topic_2 = (
        KTopic("test-csv-topic-1"),
        KTopic("test-csv-topic-2", partition_no=2),
    )
    _range = 3

    for i in range(_range):
        for t in [topic_1, topic_2]:
            for p_idx, p in enumerate(t.partitions):
                individual = i + _range * p_idx
                p.append(
                    KMessage(
                        topic=t.name,
                        partition=individual % t.partition_no,
                        offset=individual // t.partition_no,
                        key=f"key_{individual}".encode(),
                        value=f"value_{individual}".encode(),
                        timestamp=(
                            int(datetime.now().timestamp() * 1000),
                            TIMESTAMP_CREATE_TIME,
                        ),
                        headers=[("header_key", b"header_value")] if individual % 2 == 0 else None,
                    )
                )
                sleep(0.1)

    for t in [topic_1, topic_2]:
        for p in t.partitions:
            p._heap.sort(key=lambda x: x.timestamp()[1])

    render_csv([topic_1, topic_2])


def test_render_json() -> None:
    """Test rendering CSV output."""
    topic_1, topic_2 = (
        KTopic("test-csv-topic-1"),
        KTopic("test-csv-topic-2", partition_no=2),
    )
    _range = 3

    for i in range(_range):
        for t in [topic_1, topic_2]:
            for p_idx, p in enumerate(t.partitions):
                individual = i + _range * p_idx
                p.append(
                    KMessage(
                        topic=t.name,
                        partition=individual % t.partition_no,
                        offset=individual // t.partition_no,
                        key=f"key_{individual}".encode(),
                        value=f"value_{individual}".encode(),
                        timestamp=(
                            int(datetime.now().timestamp() * 1000),
                            TIMESTAMP_CREATE_TIME,
                        ),
                        headers=[("header_key", b"header_value")] if individual % 2 == 0 else None,
                    )
                )
                sleep(0.1)

    for t in [topic_1, topic_2]:
        for p in t.partitions:
            p._heap.sort(key=lambda x: x.timestamp()[1])

    render_json([topic_1, topic_2])

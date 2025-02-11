from datetime import UTC, datetime
from functools import reduce
from pathlib import Path
from platform import system
from typing import Any, Literal, Optional

from jinja2 import Environment, FileSystemLoader

from kafka_mocha.models import KTopic

INTERNAL_TOPICS = [
    "__consumer_offsets",
    "__transaction_state",
    "__schema_registry",
    "__confluent",
    "__kafka_connect",
    "_schemas",
]
environment = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))


def _prepare_records(topics: list[KTopic]) -> list[dict[str, Any]]:
    """Prepares records for rendering. Merge records from all partitions and sort them by timestamp."""
    topic_records = []
    for topic in topics:
        topic_records.append(
            {
                "name": topic.name,
                "messages": sorted(
                    reduce(lambda x, y: x + y, [partition._heap for partition in topic.partitions], []),
                    key=lambda x: x[5][1],
                ),
            }
        )
    return topic_records


def render_html(topics: list[KTopic], **kwargs) -> None:
    """Renders HTML output from the records sent to Kafka."""
    template = environment.get_template("messages.html.jinja")
    topic_records = _prepare_records(topics)
    output_name = kwargs.get("name", "messages.html")
    include_markers = kwargs.get("include_markers", False)

    content = template.render(
        timestamp=datetime.now().astimezone().isoformat(timespec="seconds").replace("+", " + "),
        os=system(),
        topics=topic_records,
        include_markers=include_markers,
    )
    with open(output_name, mode="w", encoding="utf-8") as output:
        output.write(content)


def render_csv(topics: list[KTopic], **kwargs) -> None:
    """Renders CSV output from the records sent to Kafka."""
    template = environment.get_template("messages.csv.jinja")
    topic_records = _prepare_records(topics)

    include_markers = kwargs.get("include_markers", False)

    for topic in topic_records:
        output_name = topic["name"] + ".csv"
        content = template.render(messages=topic["messages"], include_markers=include_markers)
        content = "\n".join(
            [line.replace("# Topic:", "\n# Topic:") for line in content.split("\n") if line.strip() != ""]
        )
        with open(output_name, mode="w", encoding="utf-8") as output:
            output.write(content)


def render(output: Literal["html", "csv"], records: list[KTopic], **kwargs) -> None:
    """Strategy pattern for rendering output."""
    include_internal_topics = kwargs.pop("include_internal_topics", False)
    if not include_internal_topics:
        records = [topic for topic in records if topic.name not in INTERNAL_TOPICS]

    match output:
        case "html":
            render_html(records, **kwargs)
        case "csv":
            render_csv(records, **kwargs)
        case _:
            raise ValueError(f"Unsupported output format: {output}")

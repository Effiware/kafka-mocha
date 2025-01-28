from datetime import UTC, datetime
from functools import reduce
from pathlib import Path
from platform import system
from typing import Any, Literal, Optional

from jinja2 import Environment, FileSystemLoader

from kafka_mocha.models import KTopic

environment = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))


def _prepare_records(topics: list[KTopic]) -> list[dict[str, Any]]:
    """Prepares records for rendering."""
    topic_records = []
    for topic in topics:
        topic_records.append(
            {
                "name": topic.name,
                "messages": reduce(lambda x, y: x + y, [partition._heap for partition in topic.partitions], []),
            }
        )
    return topic_records


def render_html(topics: list[KTopic], output_name: str = "messages.html") -> None:
    """Renders HTML output from the records sent to Kafka."""
    template = environment.get_template("messages.html.jinja")
    topic_records = _prepare_records(topics)
    content = template.render(timestamp=datetime.now(UTC).isoformat(), os=system(), topics=topic_records)
    with open(output_name, mode="w", encoding="utf-8") as output:
        output.write(content)


def render_csv(topics: list[KTopic], output_name: str = "messages.csv") -> None:
    """Renders CSV output from the records sent to Kafka."""
    template = environment.get_template("messages.csv.jinja")
    topic_records = _prepare_records(topics)
    content = template.render(topics=topic_records)
    content = "\n".join([line.replace("# Topic:", "\n# Topic:") for line in content.split("\n") if line.strip() != ""])[
        1:
    ]

    with open(output_name, mode="w", encoding="utf-8") as output:
        output.write(content)


def render(output: Literal["html", "csv"], records: list[KTopic], output_name: Optional[str] = None) -> None:
    """Strategy pattern for rendering output."""
    if output == "html":
        render_html(records, output_name) if output_name else render_html(records)
    elif output == "csv":
        render_csv(records, output_name) if output_name else render_csv(records)
    else:
        raise ValueError(f"Unsupported output format: {output}")

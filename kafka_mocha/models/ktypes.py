from typing import Literal, TypeVar

LogLevelType = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
OutputFormat = Literal["html", "csv"]
InputFormat = dict[
    Literal["source", "topic", "serialize", "subject_name_strategy"],
    str | bool | list[dict],
]

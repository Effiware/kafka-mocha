from typing import TypeVar, Literal

LogLevelType = TypeVar("LogLevelType", bound=Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
OutputFormat = TypeVar("OutputFormat", bound=Literal["html", "csv"])
InputFormat = TypeVar("InputFormat", bound=dict[Literal["source", "topic", "serialize"], str | bool])

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    engine: str
    title: str
    url: str
    snippet: str = ""
    rank: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadedDocument:
    result: SearchResult
    text: str
    title: str = ""
    error: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class SearchFailure:
    engine: str
    error: str

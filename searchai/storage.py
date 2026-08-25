from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import DownloadedDocument, SearchFailure, SearchResult


def slugify(value: str, max_length: int = 70) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return (slug or "consulta")[:max_length].rstrip("-")


def create_output_dir(query: str, engines: tuple[str, ...], root: Path | None = None) -> Path:
    root = root or (Path.home() / "searchai")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    engine_slug = "-".join(sorted(set(engines)))
    output_dir = root / f"{timestamp}_{engine_slug}_{slugify(query)}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def write_document(directory: Path, index: int, document: DownloadedDocument) -> str:
    filename = f"{index:03d}_{slugify(document.title or document.result.url, 50)}.md"
    path = directory / filename
    sources = ", ".join(document.result.metadata.get("engines", [document.result.engine]))
    content = f"# {document.title or document.result.title}\n\n"
    content += f"- URL: {document.result.url}\n- Motor(es): {sources}\n\n{document.text}\n"
    path.write_text(content, encoding="utf-8")
    document.path = filename
    return filename


def format_links(results: list[SearchResult]) -> str:
    lines = ["## Links encontrados", ""]
    for index, result in enumerate(results, 1):
        title = result.title.strip() or result.url
        lines.append(f"{index}. [{title}]({result.url})")
    return "\n".join(lines)


def write_manifest(
    directory: Path,
    query: str,
    engines: tuple[str, ...],
    results: list[SearchResult],
    documents: list[DownloadedDocument],
    failures: list[SearchFailure],
) -> None:
    documents_by_url = {document.result.url: document for document in documents}
    entries: list[dict[str, Any]] = []
    for index, result in enumerate(results, 1):
        document = documents_by_url.get(result.url)
        entries.append({
            "rank": index,
            "engine": result.engine,
            "title": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "download": "ok" if document and not document.error else "error",
            "error": document.error if document else "não baixado",
            "file": document.path if document else None,
        })
    payload = {"query": query, "engines": list(engines), "created_at": datetime.now().isoformat(), "results": entries,
              "search_failures": [failure.__dict__ for failure in failures]}
    (directory / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

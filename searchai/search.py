from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Protocol

import httpx
from ddgs import DDGS

from .models import SearchResult


class SearchEngine(Protocol):
    name: str

    def search(self, query: str, max_results: int) -> list[SearchResult]: ...


class DuckDuckGoEngine:
    name = "duckduckgo"

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            rows = DDGS().text(query, max_results=max_results)
        except Exception as exc:
            # DDGS raises this when no entries are returned; treat as an empty search.
            if "No results found" in str(exc):
                return []
            raise
        return [
            SearchResult(
                engine=self.name,
                title=str(row.get("title", "")),
                url=str(row.get("href", "")),
                snippet=str(row.get("body", "")),
                rank=index,
            )
            for index, row in enumerate(rows, 1)
            if row.get("href")
        ]


class GoogleEngine:
    name = "google"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        options = options or {}
        self.api_key = str(options.get("api_key") or os.getenv("GOOGLE_API_KEY", ""))
        self.search_engine_id = str(options.get("search_engine_id") or os.getenv("GOOGLE_CSE_ID", ""))
        self.client = httpx.Client(timeout=float(options.get("timeout", 20)))

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.api_key or not self.search_engine_id:
            raise RuntimeError("Google requer GOOGLE_API_KEY e GOOGLE_CSE_ID")
        response = self.client.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": self.api_key, "cx": self.search_engine_id, "q": query, "num": min(max_results, 10)},
        )
        response.raise_for_status()
        return [
            SearchResult(
                engine=self.name,
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                rank=index,
            )
            for index, item in enumerate(response.json().get("items", []), 1)
            if item.get("link")
        ]


class BingEngine:
    name = "bing"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        options = options or {}
        self.api_key = str(options.get("api_key") or os.getenv("BING_API_KEY", ""))
        self.endpoint = str(options.get("endpoint", "https://api.bing.microsoft.com/v7.0/search"))
        self.client = httpx.Client(timeout=float(options.get("timeout", 20)))

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self.api_key:
            raise RuntimeError("Bing requer BING_API_KEY")
        response = self.client.get(
            self.endpoint,
            headers={"Ocp-Apim-Subscription-Key": self.api_key},
            params={"q": query, "count": max_results, "textDecorations": False, "textFormat": "Raw"},
        )
        response.raise_for_status()
        return [
            SearchResult(
                engine=self.name,
                title=item.get("name", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                rank=index,
            )
            for index, item in enumerate(response.json().get("webPages", {}).get("value", []), 1)
            if item.get("url")
        ]


ENGINE_FACTORIES: dict[str, Callable[[dict[str, Any] | None], SearchEngine]] = {
    "duckduckgo": lambda options=None: DuckDuckGoEngine(),
    "google": GoogleEngine,
    "bing": BingEngine,
}


def build_engine(name: str, options: dict[str, Any] | None = None) -> SearchEngine:
    try:
        return ENGINE_FACTORIES[name](options)
    except KeyError as exc:
        raise ValueError(f"motor não suportado: {name}") from exc

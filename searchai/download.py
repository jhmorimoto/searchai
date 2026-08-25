from __future__ import annotations

import re
from html import unescape

import httpx
import trafilatura

from .models import DownloadedDocument, SearchResult

USER_AGENT = "searchai/0.1 (+https://localhost)"


def extract_text(html: str) -> str:
    extracted = trafilatura.extract(html, include_links=True, include_tables=True)
    if extracted:
        return extracted.strip()
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def download_result(result: SearchResult, timeout: float = 20.0, max_bytes: int = 2_000_000) -> DownloadedDocument:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(result.url)
            response.raise_for_status()
            content = response.content
            if len(content) > max_bytes:
                raise ValueError(f"conteúdo excede o limite de {max_bytes} bytes")
            text = extract_text(response.text)
            if not text:
                raise ValueError("nenhum texto extraído")
            return DownloadedDocument(result=result, title=result.title, text=text)
    except (httpx.HTTPError, UnicodeError, ValueError) as exc:
        return DownloadedDocument(result=result, title=result.title, text="", error=str(exc))

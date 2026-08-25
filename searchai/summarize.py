from __future__ import annotations

import os
import sys
from pathlib import Path

from openai import OpenAI

from .config import DEFAULT_ENDPOINT
from .models import DownloadedDocument

PROMPT_FILENAME = "PROMPT.md"
DEFAULT_CHATGPT_MODEL = "gpt-4.1-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def _log_model_request(provider: str, model: str, documents: list[DownloadedDocument]) -> None:
    print("\n=== SUMMARIZING SEARCH RESULT ===", file=sys.stderr)
    print(f"provider: {provider}", file=sys.stderr)
    print(f"model: {model}", file=sys.stderr)
    print("sources:", file=sys.stderr)
    for index, document in enumerate(documents, 1):
        title = document.title or document.result.title
        print(f"{index}. title: {title}", file=sys.stderr)
        print(f"   url: {document.result.url}", file=sys.stderr)
    print("===================================\n", file=sys.stderr)


def _normalize_base_url(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    return normalized if normalized.endswith("/v1") else normalized + "/v1"


def _build_client(provider: str, endpoint: str, api_key: str | None, model_timeout: float) -> OpenAI:
    if provider == "chatgpt":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("defina OPENAI_API_KEY ou use --api-key para usar o provedor chatgpt")
        kwargs = {"api_key": key, "timeout": model_timeout}
        if endpoint and endpoint.rstrip("/") != DEFAULT_ENDPOINT:
            kwargs["base_url"] = _normalize_base_url(endpoint)
        return OpenAI(**kwargs)
    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("defina GEMINI_API_KEY/GOOGLE_API_KEY ou use --api-key para usar o provedor gemini")
        return OpenAI(base_url=_normalize_base_url(endpoint), api_key=key, timeout=model_timeout)
    return OpenAI(base_url=_normalize_base_url(endpoint), api_key="lm-studio", timeout=model_timeout)


def load_prompt_instructions(query: str, prompt_path: Path | None = None) -> str:
    path = prompt_path or (Path.cwd() / PROMPT_FILENAME)
    try:
        instructions = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"não foi possível ler o prompt {path}: {exc}") from exc
    if not instructions:
        raise RuntimeError(f"o prompt {path} está vazio")
    return instructions.replace("INCLUIR_TERMOS_DA_BUSCA_ORIGINAL", query)


def summarize(
    provider: str,
    endpoint: str,
    api_key: str | None,
    query: str,
    documents: list[DownloadedDocument],
    model: str | None = None,
    max_prompt_chars: int = 100_000,
    model_timeout: float = 600.0,
) -> str:
    instructions = load_prompt_instructions(query)
    client = _build_client(provider, endpoint, api_key, model_timeout)
    if model:
        selected_model = model
    elif provider == "chatgpt":
        selected_model = DEFAULT_CHATGPT_MODEL
    elif provider == "gemini":
        selected_model = DEFAULT_GEMINI_MODEL
    else:
        selected_model = next(iter(client.models.list().data)).id
    sections: list[str] = []
    user_prefix = f"Consulta: {query}\nFontes:"
    remaining = max_prompt_chars - len(user_prefix)
    for index, document in enumerate(documents, 1):
        section = f"\n\n[Fonte {index}] {document.title or document.result.title}\nURL: {document.result.url}\n{document.text}"
        if remaining <= 0:
            break
        sections.append(section[:remaining])
        remaining -= len(section)
    prompt = f"{user_prefix}{''.join(sections)}"
    _log_model_request(provider, selected_model, documents)
    response = client.chat.completions.create(
        model=selected_model,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"o provedor {provider} retornou um resumo vazio")
    return content.strip()

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from .models import DownloadedDocument

PROMPT_FILENAME = "PROMPT.md"


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
    endpoint: str,
    query: str,
    documents: list[DownloadedDocument],
    model: str | None = None,
    max_prompt_chars: int = 100_000,
) -> str:
    instructions = load_prompt_instructions(query)
    client = OpenAI(base_url=endpoint.rstrip("/") + "/v1", api_key="lm-studio", timeout=60.0)
    selected_model = model or next(iter(client.models.list().data)).id
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
        raise RuntimeError("LMStudio retornou um resumo vazio")
    return content.strip()

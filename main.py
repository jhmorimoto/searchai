from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from searchai.config import ConfigError, load_config, merge_cli
from searchai.download import download_result
from searchai.models import DownloadedDocument, SearchFailure, SearchResult
from searchai.search import build_engine
from searchai.storage import create_output_dir, format_links, write_document, write_manifest
from searchai.summarize import summarize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pesquisa na internet e resume com LMStudio.")
    parser.add_argument("--config", help="caminho do arquivo YAML de configuração")
    parser.add_argument("terms", nargs="*", help="termos da pesquisa; sem termos posicionais, lê uma linha do stdin")
    parser.add_argument("--api-endpoint")
    parser.add_argument("--search-engine", action="append", dest="engines", metavar="NOME")
    parser.add_argument("--max-results", type=int)
    parser.add_argument("--download-timeout", type=float, dest="download_timeout")
    parser.add_argument("--max-download-bytes", type=int, dest="max_download_bytes")
    parser.add_argument("--max-prompt-chars", type=int, dest="max_prompt_chars")
    parser.add_argument("--model")
    return parser.parse_args()


def unique_results(results: list[SearchResult]) -> list[SearchResult]:
    unique: OrderedDict[str, SearchResult] = OrderedDict()
    for result in results:
        if result.url in unique:
            current = unique[result.url]
            engines = list(current.metadata.get("engines", [current.engine]))
            if result.engine not in engines:
                engines.append(result.engine)
            unique[result.url] = SearchResult(**{**current.__dict__, "metadata": {"engines": engines}})
        else:
            unique[result.url] = SearchResult(**{**result.__dict__, "metadata": {"engines": [result.engine]}})
    return list(unique.values())


def run(args: argparse.Namespace) -> int:
    config = merge_cli(
        load_config(args.config),
        api_endpoint=args.api_endpoint,
        engines=args.engines,
        max_results=args.max_results,
        download_timeout=args.download_timeout,
        max_download_bytes=args.max_download_bytes,
        max_prompt_chars=args.max_prompt_chars,
        model=args.model,
    )
    query = " ".join(args.terms).strip() if args.terms else sys.stdin.readline().strip()
    if not query:
        raise ConfigError("informe uma consulta com argumentos posicionais ou stdin")

    output_dir = create_output_dir(query, config.engines)
    results: list[SearchResult] = []
    failures: list[SearchFailure] = []
    for engine_name in config.engines:
        try:
            engine = build_engine(engine_name, config.engines_config.get(engine_name))
            engine_results = engine.search(query, config.max_results)
            results.extend(engine_results)
            for result in engine_results:
                print(f"{result.rank}. [{result.engine}] {result.title} - {result.url}")
        except Exception as exc:
            failures.append(SearchFailure(engine_name, str(exc)))
            print(f"Erro no motor {engine_name}: {exc}", file=sys.stderr)

    results = unique_results(results)
    documents: list[DownloadedDocument] = []
    for index, result in enumerate(results, 1):
        document = download_result(result, config.download_timeout, config.max_download_bytes)
        if document.error:
            print(f"Erro ao baixar {result.url}: {document.error}", file=sys.stderr)
        else:
            document.text = summarize(
                config.api_endpoint,
                query,
                [document],
                config.model,
                config.max_prompt_chars,
            )
            write_document(output_dir, index, document)
            documents.append(document)
    write_manifest(output_dir, query, config.engines, results, documents, failures)
    if not documents:
        raise RuntimeError(f"nenhum conteúdo foi baixado; resultados em {output_dir}")

    summary = summarize(config.api_endpoint, query, documents, config.model, config.max_prompt_chars)
    summary_with_links = f"{summary}\n\n{format_links(results)}\n"
    (output_dir / "summary.md").write_text(summary_with_links, encoding="utf-8")
    print(f"\nResumo:\n{summary_with_links}\nArquivos: {output_dir}")
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except (ConfigError, RuntimeError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Erro ao acessar o LMStudio ou executar a pesquisa: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

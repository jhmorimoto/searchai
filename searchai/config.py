from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

import yaml

DEFAULT_ENDPOINT = "http://127.0.0.1:1234"
CONFIG_FILENAME = "config.yaml"
DEFAULT_CONFIG_PATHS = (
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / ".config" / "searchai" / CONFIG_FILENAME,
)
SUPPORTED_ENGINES = frozenset({"duckduckgo", "google", "bing"})


class ConfigError(ValueError):
    """Raised when the SEARCHAI configuration is invalid."""


@dataclass(frozen=True)
class AppConfig:
    api_endpoint: str = DEFAULT_ENDPOINT
    engines: tuple[str, ...] = ("duckduckgo",)
    engines_config: dict[str, dict[str, Any]] = field(default_factory=dict)
    max_results: int = 5
    download_timeout: float = 20.0
    max_download_bytes: int = 2_000_000
    max_prompt_chars: int = 100_000
    model: str | None = None
    config_path: Path | None = None


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"'{name}' deve ser um objeto YAML")
    return value


def _parse_engines(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError("'engines' deve ser uma lista não vazia")
    engines = tuple(str(item).strip().lower() for item in value)
    invalid = sorted(set(engines) - SUPPORTED_ENGINES)
    if invalid:
        supported = ", ".join(sorted(SUPPORTED_ENGINES))
        raise ConfigError(f"motores desconhecidos: {', '.join(invalid)}; disponíveis: {supported}")
    if any(not engine for engine in engines):
        raise ConfigError("'engines' não pode conter nomes vazios")
    return engines


def _positive_number(value: Any, name: str, integer: bool = False) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"'{name}' deve ser um número positivo")
    if integer and not isinstance(value, int):
        raise ConfigError(f"'{name}' deve ser um inteiro positivo")
    return value


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load explicit YAML or the first existing automatic configuration file."""
    if path is not None:
        config_path = Path(path).expanduser()
    else:
        config_path = next((candidate for candidate in DEFAULT_CONFIG_PATHS if candidate.exists()), None)
        if config_path is None:
            return AppConfig()
    if not config_path.exists():
        raise ConfigError(f"arquivo de configuração não encontrado: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"não foi possível ler {config_path}: {exc}") from exc
    data = _require_mapping(raw, "configuração")

    engines = _parse_engines(data["engines"]) if "engines" in data else AppConfig.engines
    engines_config = data.get("engines_config", {})
    engines_config = _require_mapping(engines_config, "engines_config")
    normalized_config: dict[str, dict[str, Any]] = {}
    for engine, options in engines_config.items():
        if str(engine).lower() not in SUPPORTED_ENGINES:
            raise ConfigError(f"configuração para motor desconhecido: {engine}")
        normalized_config[str(engine).lower()] = dict(_require_mapping(options, f"engines_config.{engine}"))

    values: dict[str, Any] = {"config_path": config_path}
    for name in ("api_endpoint", "model"):
        if name in data:
            if name == "api_endpoint" and not isinstance(data[name], str):
                raise ConfigError("'api_endpoint' deve ser texto")
            if name == "model" and data[name] is not None and not isinstance(data[name], str):
                raise ConfigError("'model' deve ser texto")
            values[name] = data[name]
    if "max_results" in data:
        values["max_results"] = _positive_number(data["max_results"], "max_results", integer=True)
    if "download_timeout" in data:
        values["download_timeout"] = _positive_number(data["download_timeout"], "download_timeout")
    for name in ("max_download_bytes", "max_prompt_chars"):
        if name in data:
            values[name] = _positive_number(data[name], name, integer=True)
    values["engines"] = engines
    values["engines_config"] = normalized_config
    return replace(AppConfig(), **values)


def merge_cli(config: AppConfig, **overrides: Any) -> AppConfig:
    """Apply explicitly provided CLI values over YAML values."""
    values = {key: value for key, value in overrides.items() if value is not None}
    if "engines" in values:
        values["engines"] = _parse_engines(values["engines"])
    return replace(config, **values)

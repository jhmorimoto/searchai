from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

DEFAULT_ENDPOINT = "http://127.0.0.1:1234"
DEFAULT_CHATGPT_ENDPOINT = "https://api.openai.com"
DEFAULT_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL_TIMEOUT = 600.0
DEFAULT_AI_PROVIDER = "lmstudio"
CONFIG_FILENAME = "config.yaml"
DEFAULT_CONFIG_PATHS = (
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / ".config" / "searchai" / CONFIG_FILENAME,
)
SUPPORTED_ENGINES = frozenset({"duckduckgo", "google", "bing"})
SUPPORTED_AI_PROVIDERS = frozenset({"lmstudio", "chatgpt", "gemini"})


class ConfigError(ValueError):
    """Raised when the SEARCHAI configuration is invalid."""


@dataclass(frozen=True)
class AppConfig:
    api_endpoint: str = DEFAULT_ENDPOINT
    ai_provider: str = DEFAULT_AI_PROVIDER
    api_key: str | None = None
    engines: tuple[str, ...] = ("duckduckgo",)
    engines_config: dict[str, dict[str, Any]] = field(default_factory=dict)
    max_results: int = 5
    download_timeout: float = 20.0
    max_download_bytes: int = 2_000_000
    max_prompt_chars: int = 100_000
    model_timeout: float = DEFAULT_MODEL_TIMEOUT
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


def _parse_duration_seconds(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ConfigError(f"'{name}' deve ser um número positivo ou duração (ex.: 10m, 4h, 2d)")
    if isinstance(value, (int, float)):
        if value <= 0:
            raise ConfigError(f"'{name}' deve ser maior que zero")
        return float(value)
    if not isinstance(value, str):
        raise ConfigError(f"'{name}' deve ser um número positivo ou duração (ex.: 10m, 4h, 2d)")

    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([smhdSMHD])?\s*", value)
    if not match:
        raise ConfigError(f"'{name}' inválido: use segundos ou formato com sufixo s/m/h/d (ex.: 10m)")

    amount = float(match.group(1))
    if amount <= 0:
        raise ConfigError(f"'{name}' deve ser maior que zero")

    unit = (match.group(2) or "s").lower()
    factor = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return amount * factor


def _parse_ai_provider(value: Any) -> str:
    if not isinstance(value, str):
        raise ConfigError("'ai_provider' deve ser texto")
    provider = value.strip().lower()
    if provider not in SUPPORTED_AI_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_AI_PROVIDERS))
        raise ConfigError(f"provedor de IA desconhecido: {provider}; disponíveis: {supported}")
    return provider


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
    provider = _parse_ai_provider(data["ai_provider"]) if "ai_provider" in data else AppConfig.ai_provider
    values["ai_provider"] = provider

    # Backward-compatible alias: accept `api_token` as `api_key`.
    if "api_token" in data:
        if "api_key" in data:
            raise ConfigError("use apenas um entre 'api_key' e 'api_token'")
        data = dict(data)
        data["api_key"] = data["api_token"]

    for name in ("api_endpoint", "model", "api_key"):
        if name in data:
            if name == "api_endpoint" and not isinstance(data[name], str):
                raise ConfigError("'api_endpoint' deve ser texto")
            if name == "model" and data[name] is not None and not isinstance(data[name], str):
                raise ConfigError("'model' deve ser texto")
            if name == "api_key" and data[name] is not None and not isinstance(data[name], str):
                raise ConfigError("'api_key' deve ser texto")
            values[name] = data[name]
    if provider == "chatgpt" and "api_endpoint" not in values:
        values["api_endpoint"] = DEFAULT_CHATGPT_ENDPOINT
    if provider == "gemini" and "api_endpoint" not in values:
        values["api_endpoint"] = DEFAULT_GEMINI_ENDPOINT
    if "max_results" in data:
        values["max_results"] = _positive_number(data["max_results"], "max_results", integer=True)
    if "download_timeout" in data:
        values["download_timeout"] = _positive_number(data["download_timeout"], "download_timeout")
    if "model_timeout" in data:
        values["model_timeout"] = _parse_duration_seconds(data["model_timeout"], "model_timeout")
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
    if "ai_provider" in values:
        values["ai_provider"] = _parse_ai_provider(values["ai_provider"])
    return replace(config, **values)

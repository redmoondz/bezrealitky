"""Loading, validation, and atomic updates for config/config.yaml."""

from __future__ import annotations

import re
import tempfile
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "defaults.yaml"
ALLOWED_HOSTS = {"bezrealitky.com", "www.bezrealitky.com"}
MARKDOWN_LINK_RE = re.compile(r"^\s*\[[^]]*]\((https?://.+)\)\s*$", re.IGNORECASE)
MAX_PRICE = 1_000_000_000


class ConfigurationError(ValueError):
    """Raised when the YAML configuration or CLI values are invalid."""


def normalize_url_input(value: str) -> str:
    """Accept a plain URL or a Markdown link copied from a message."""
    candidate = re.sub(r"&(?:amp|#38|#x26);", "&", value.strip(), flags=re.IGNORECASE)
    markdown_match = MARKDOWN_LINK_RE.match(candidate)
    if markdown_match:
        candidate = markdown_match.group(1)
    return candidate.replace(r"\&", "&").strip()


def validate_search_url(value: str) -> str:
    normalized = normalize_url_input(value)
    try:
        parsed = urlparse(normalized)
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError(f"Invalid URL: {exc}") from exc

    if parsed.scheme.lower() != "https":
        raise ConfigurationError("URL must use https")
    if parsed.hostname is None or parsed.hostname.lower() not in ALLOWED_HOSTS:
        raise ConfigurationError("URL domain must be bezrealitky.com")
    if parsed.username or parsed.password or port not in (None, 443):
        raise ConfigurationError("URL must not contain credentials or a non-standard port")
    if parsed.path.rstrip("/") != "/search":
        raise ConfigurationError("URL must point to the /search page")

    normalized_netloc = parsed.hostname.lower()
    return urlunparse(("https", normalized_netloc, "/search", "", parsed.query, parsed.fragment))


def validate_price(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field} must be an integer")
    if not 0 <= value <= MAX_PRICE:
        raise ConfigurationError(f"{field} must be between 0 and {MAX_PRICE}")
    return value


def prices_from_url(url: str) -> tuple[int | None, int | None]:
    params = parse_qsl(urlparse(url).query, keep_blank_values=True)
    found: dict[str, int] = {}
    for key, value in params:
        if key not in {"priceFrom", "priceTo"}:
            continue
        try:
            found[key] = validate_price(int(value), key)
        except ValueError as exc:
            raise ConfigurationError(f"{key} in URL must be an integer") from exc
    return found.get("priceFrom"), found.get("priceTo")


def validate_price_range(url: str) -> None:
    price_from, price_to = prices_from_url(url)
    if price_from is not None and price_to is not None and price_from > price_to:
        raise ConfigurationError("price_from must not be greater than price_to")


def set_url_prices(url: str, price_from: int | None, price_to: int | None) -> str:
    parsed = urlparse(url)
    replacements = {"priceFrom": price_from, "priceTo": price_to}
    params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in replacements or replacements[key] is None
    ]
    for key, value in replacements.items():
        if value is not None:
            params.append((key, str(validate_price(value, key))))
    updated = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
    validate_price_range(updated)
    return updated


def validate_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ConfigurationError("Config root must be a mapping")
    if config.get("version") != 1:
        raise ConfigurationError("Config version must be 1")
    search = config.get("search")
    scraper = config.get("scraper")
    if not isinstance(search, dict) or not isinstance(scraper, dict):
        raise ConfigurationError("Config must contain search and scraper mappings")

    search["url"] = validate_search_url(str(search.get("url", "")))
    validate_price_range(search["url"])

    output = str(scraper.get("output_csv", "")).strip()
    if not output or Path(output).suffix.lower() != ".csv":
        raise ConfigurationError("scraper.output_csv must be a .csv path")
    scraper["output_csv"] = output

    numeric_rules = {
        "request_timeout_seconds": (0, 300),
        "delay_seconds": (0, 60),
        "max_retries": (0, 10),
    }
    for field, (minimum, maximum) in numeric_rules.items():
        value = scraper.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(f"scraper.{field} must be numeric")
        if field == "request_timeout_seconds" and value == 0:
            raise ConfigurationError("scraper.request_timeout_seconds must be greater than zero")
        if not minimum <= value <= maximum:
            raise ConfigurationError(f"scraper.{field} must be between {minimum} and {maximum}")
    if not isinstance(scraper["max_retries"], int):
        raise ConfigurationError("scraper.max_retries must be an integer")
    if not str(scraper.get("user_agent", "")).strip():
        raise ConfigurationError("scraper.user_agent must not be empty")
    return config


def load_config(path: Path = ACTIVE_CONFIG_PATH) -> dict:
    if not path.exists():
        if path == ACTIVE_CONFIG_PATH:
            return reset_config(path)
        raise ConfigurationError(f"Config file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return validate_config(data)


def save_config(config: dict, path: Path = ACTIVE_CONFIG_PATH) -> None:
    validated = validate_config(deepcopy(config))
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary_path = Path(handle.name)
        yaml.safe_dump(validated, handle, sort_keys=False, allow_unicode=True)
    temporary_path.replace(path)


def reset_config(path: Path = ACTIVE_CONFIG_PATH) -> dict:
    if not DEFAULT_CONFIG_PATH.exists():
        raise ConfigurationError(f"Default config does not exist: {DEFAULT_CONFIG_PATH}")
    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        defaults = yaml.safe_load(handle)
    defaults = validate_config(defaults)
    save_config(defaults, path)
    return defaults


def apply_updates(
    config: dict,
    *,
    url: str | None = None,
    price_from: int | None = None,
    price_to: int | None = None,
    output: str | None = None,
    delay: float | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> dict:
    updated = deepcopy(config)
    search_url = validate_search_url(url) if url is not None else updated["search"]["url"]
    search_url = set_url_prices(search_url, price_from, price_to)
    updated["search"]["url"] = search_url
    if output is not None:
        updated["scraper"]["output_csv"] = output
    if delay is not None:
        updated["scraper"]["delay_seconds"] = delay
    if timeout is not None:
        updated["scraper"]["request_timeout_seconds"] = timeout
    if max_retries is not None:
        updated["scraper"]["max_retries"] = max_retries
    return validate_config(updated)

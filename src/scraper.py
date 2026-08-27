"""Bezrealitky search crawler and listing parser."""

from __future__ import annotations

import csv
import logging
import re
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)

LISTING_PATH_RE = re.compile(r"^/properties-flats-houses/(?P<id>\d+)(?:-|$)")
NUMBER_RE = re.compile(r"-?\d[\d\s\u00a0,.]*")
CURRENCY_RE = re.compile(r"\b[A-Z]{3}\b|[€$£]")


@dataclass(slots=True)
class Listing:
    listing_id: str = ""
    name: str = ""
    format: str = ""
    area: str = ""
    total_price: str = ""
    currency: str = ""
    url: str = ""
    available_from: str = ""
    monthly_rent: str = ""
    refundable_deposit: str = ""
    service_charges: str = ""
    utility_charges: str = ""
    price_per_unit: str = ""
    location: str = ""
    description: str = ""
    heating: str = ""
    floor: str = ""
    fully_furnished: str = ""


CSV_FIELDS = list(Listing.__dataclass_fields__)


def clean_text(value: str | None) -> str:
    """Collapse HTML whitespace while preserving readable text."""
    return " ".join((value or "").replace("\xa0", " ").split())


def build_session(user_agent: str, max_retries: int) -> requests.Session:
    """Create an HTTP session with bounded retries for transient failures."""
    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        status=max_retries,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }
    )
    return session


def fetch_html(session: requests.Session, url: str, timeout: float) -> str:
    """Fetch one HTML page and raise on HTTP or non-HTML responses."""
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        raise ValueError(f"Expected HTML from {url}, received {content_type!r}")
    return response.text


def extract_listing_urls(content: str, page_url: str) -> list[str]:
    """Return unique publication URLs from a search-results page."""
    soup = BeautifulSoup(content, "html.parser")
    result: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if not LISTING_PATH_RE.match(parsed.path):
            continue
        canonical = parsed._replace(query="", fragment="").geturl()
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def extract_next_page_url(content: str, page_url: str) -> str | None:
    """Find the search pagination link labelled ``Next``."""
    soup = BeautifulSoup(content, "html.parser")
    for anchor in soup.select("a[href]"):
        if clean_text(anchor.get_text(" ", strip=True)).casefold() != "next":
            continue
        absolute = urljoin(page_url, str(anchor.get("href")))
        if urlparse(absolute).path.rstrip("/") == "/search":
            return absolute
    return None


def parse_page(content: str, page_url: str) -> tuple[list[str], str | None]:
    """Parse one search page into publication URLs and the next-page URL."""
    return extract_listing_urls(content, page_url), extract_next_page_url(content, page_url)


def discover_listing_urls(
    session: requests.Session,
    start_url: str,
    timeout: float,
    delay_seconds: float,
) -> list[str]:
    """Walk pagination until no unseen next page remains."""
    current_url: str | None = start_url
    visited_pages: set[str] = set()
    listing_urls: list[str] = []
    seen_listings: set[str] = set()

    while current_url and current_url not in visited_pages:
        visited_pages.add(current_url)
        LOGGER.info("Reading search page %d: %s", len(visited_pages), current_url)
        content = fetch_html(session, current_url, timeout)
        page_listings, next_url = parse_page(content, current_url)
        for listing_url in page_listings:
            if listing_url not in seen_listings:
                seen_listings.add(listing_url)
                listing_urls.append(listing_url)
        LOGGER.info(
            "Found %d publications on this page (%d unique total)",
            len(page_listings),
            len(listing_urls),
        )
        current_url = next_url
        if current_url and current_url not in visited_pages and delay_seconds:
            time.sleep(delay_seconds)

    return listing_urls


def extract_table_values(soup: BeautifulSoup) -> dict[str, str]:
    """Extract label/value pairs from the publication detail tables."""
    values: dict[str, str] = {}
    for row in soup.select("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) < 2:
            cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = clean_text(cells[0].get_text(" ", strip=True)).casefold()
        value = clean_text(cells[-1].get_text(" ", strip=True))
        if label:
            values.setdefault(label, value)
    return values


def extract_labeled_value(soup: BeautifulSoup, label: str) -> str:
    """Find a strong value located next to a visible price label."""
    wanted = label.casefold()
    for text_node in soup.find_all(string=True):
        if clean_text(str(text_node)).lstrip("+ ").casefold() != wanted:
            continue
        parent: Tag | None = text_node.parent if isinstance(text_node.parent, Tag) else None
        for _ in range(5):
            if parent is None:
                break
            strong = parent.find("strong")
            if strong is not None:
                return clean_text(strong.get_text(" ", strip=True))
            parent = parent.parent if isinstance(parent.parent, Tag) else None
    return ""


def parse_number(value: str) -> Decimal | None:
    """Parse an English-formatted numeric value embedded in text."""
    match = NUMBER_RE.search(clean_text(value))
    if not match:
        return None
    number = match.group(0).replace(" ", "").replace("\xa0", "")
    if "," in number and "." in number:
        number = number.replace(",", "")
    elif "," in number:
        tail = number.rsplit(",", 1)[-1]
        number = number.replace(",", "") if len(tail) == 3 else number.replace(",", ".")
    try:
        return Decimal(number)
    except InvalidOperation:
        return None


def format_number(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value.normalize(), "f")


def extract_currency(*values: str) -> str:
    aliases = {"€": "EUR", "$": "USD", "£": "GBP"}
    for value in values:
        match = CURRENCY_RE.search(value)
        if match:
            return aliases.get(match.group(0), match.group(0))
    return ""


def extract_description(soup: BeautifulSoup) -> str:
    panel = soup.select_one('[role="tabpanel"]')
    if panel is None:
        return ""
    paragraphs = [clean_text(item.get_text(" ", strip=True)) for item in panel.select("p")]
    paragraphs = [item for item in paragraphs if item]
    return "\n".join(paragraphs) if paragraphs else clean_text(panel.get_text(" ", strip=True))


def extract_heading(soup: BeautifulSoup) -> tuple[str, str]:
    heading = soup.find("h1")
    if heading is None:
        return "", ""
    name = clean_text(heading.get_text(" ", strip=True))
    spans = heading.find_all("span", recursive=False)
    location = clean_text(spans[-1].get_text(" ", strip=True)) if len(spans) >= 2 else ""
    return name, location


def parse_listing(content: str, listing_url: str) -> Listing:
    """Parse one publication detail page into a normalized CSV row."""
    soup = BeautifulSoup(content, "html.parser")
    table = extract_table_values(soup)
    name, location = extract_heading(soup)

    monthly_raw = extract_labeled_value(soup, "Monthly rent")
    service_raw = extract_labeled_value(soup, "Service charges")
    utilities_raw = extract_labeled_value(soup, "Utility charges")
    deposit_raw = extract_labeled_value(soup, "Refundable deposit")
    monthly = parse_number(monthly_raw)
    service = parse_number(service_raw)
    utilities = parse_number(utilities_raw)
    recurring = [value for value in (monthly, service, utilities) if value is not None]

    listing_id = table.get("listing id", "")
    if not listing_id:
        path_match = LISTING_PATH_RE.match(urlparse(listing_url).path)
        listing_id = path_match.group("id") if path_match else ""

    price_per_unit_raw = table.get("price per unit", "")
    return Listing(
        listing_id=listing_id,
        name=name,
        format=table.get("layout", ""),
        area=format_number(parse_number(table.get("usable area", ""))),
        total_price=format_number(sum(recurring, Decimal("0"))) if recurring else "",
        currency=extract_currency(monthly_raw, service_raw, utilities_raw, price_per_unit_raw),
        url=listing_url,
        available_from=table.get("available from", ""),
        monthly_rent=format_number(monthly),
        refundable_deposit=format_number(parse_number(deposit_raw)),
        service_charges=format_number(service),
        utility_charges=format_number(utilities),
        price_per_unit=format_number(parse_number(price_per_unit_raw)),
        location=location,
        description=extract_description(soup),
        heating=table.get("heating", ""),
        floor=table.get("floor", ""),
        fully_furnished=table.get("fully furnished", ""),
    )


def write_csv(path: Path, listings: Iterable[Listing]) -> int:
    """Write listings to UTF-8 CSV and return the written row count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for listing in listings:
            writer.writerow(asdict(listing))
            handle.flush()
            count += 1
    return count


def scrape(config: dict) -> tuple[int, list[str]]:
    """Discover every publication, parse it, and save the results to CSV."""
    search = config["search"]
    settings = config["scraper"]
    timeout = float(settings["request_timeout_seconds"])
    delay = float(settings["delay_seconds"])
    session = build_session(str(settings["user_agent"]), int(settings["max_retries"]))

    try:
        urls = discover_listing_urls(session, str(search["url"]), timeout, delay)
        LOGGER.info("Discovered %d unique publications", len(urls))
        parsed: list[Listing] = []
        failures: list[str] = []
        for index, listing_url in enumerate(urls, start=1):
            LOGGER.info("Parsing publication %d/%d: %s", index, len(urls), listing_url)
            try:
                parsed.append(parse_listing(fetch_html(session, listing_url, timeout), listing_url))
            except (requests.RequestException, ValueError) as exc:
                LOGGER.error("Could not parse %s: %s", listing_url, exc)
                failures.append(listing_url)
            if index < len(urls) and delay:
                time.sleep(delay)

        output_path = Path(str(settings["output_csv"]))
        written = write_csv(output_path, parsed)
        LOGGER.info("Saved %d publications to %s", written, output_path)
        return written, failures
    finally:
        session.close()


def main() -> int:
    try:
        from .configuration import load_config
    except ImportError:  # Support: python3 src/scraper.py
        from configuration import load_config

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    written, failures = scrape(load_config())
    if failures:
        LOGGER.error("Finished with %d failed publications", len(failures))
        return 1
    LOGGER.info("Finished successfully: %d publications", written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI for editing config/config.yaml and optionally running the scraper."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

try:
    from .configuration import (
        ACTIVE_CONFIG_PATH,
        ConfigurationError,
        apply_updates,
        load_config,
        reset_config,
        save_config,
    )
    from .scraper import scrape
except ImportError:  # Support: python3 src/cli.py
    from configuration import (  # type: ignore[no-redef]
        ACTIVE_CONFIG_PATH,
        ConfigurationError,
        apply_updates,
        load_config,
        reset_config,
        save_config,
    )
    from scraper import scrape  # type: ignore[no-redef]


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and edit config/config.yaml for the Bezrealitky scraper."
    )
    parser.add_argument(
        "--url",
        "--import-url",
        dest="url",
        help="import a Bezrealitky /search URL (plain or Markdown-formatted)",
    )
    parser.add_argument("--price-from", "--price_from", type=non_negative_int)
    parser.add_argument("--price-to", "--price_to", type=non_negative_int)
    parser.add_argument("--output", help="CSV output path")
    parser.add_argument("--delay", type=non_negative_float, help="delay between requests")
    parser.add_argument("--timeout", type=positive_float, help="request timeout in seconds")
    parser.add_argument("--max-retries", type=non_negative_int)
    parser.add_argument("--reset", action="store_true", help="restore config defaults")
    parser.add_argument("--show", action="store_true", help="print the resulting config")
    parser.add_argument("--run", action="store_true", help="run the scraper after saving")
    parser.add_argument(
        "--config",
        type=Path,
        default=ACTIVE_CONFIG_PATH,
        help=argparse.SUPPRESS,
    )
    return parser


def has_updates(args: argparse.Namespace) -> bool:
    return any(
        value is not None
        for value in (
            args.url,
            args.price_from,
            args.price_to,
            args.output,
            args.delay,
            args.timeout,
            args.max_retries,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.reset and has_updates(args):
        parser.error("--reset cannot be combined with config update options")

    try:
        if args.reset:
            config = reset_config(args.config)
            print(f"Defaults restored in {args.config}")
        else:
            config = load_config(args.config)
            if has_updates(args):
                config = apply_updates(
                    config,
                    url=args.url,
                    price_from=args.price_from,
                    price_to=args.price_to,
                    output=args.output,
                    delay=args.delay,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                )
                save_config(config, args.config)
                print(f"Config saved to {args.config}")

        if args.show or (not args.run and not args.reset and not has_updates(args)):
            print(yaml.safe_dump(config, sort_keys=False, allow_unicode=True).rstrip())

        if args.run:
            logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
            written, failures = scrape(config)
            print(f"Saved {written} publications to {config['scraper']['output_csv']}")
            if failures:
                print(f"Failed publications: {len(failures)}", file=sys.stderr)
                return 1
        return 0
    except (ConfigurationError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

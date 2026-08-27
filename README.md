# Bezrealitky CSV parser

The parser reads every page of a Bezrealitky search, deduplicates publication
links, opens every publication, and writes the normalized data to CSV.

The `images` CSV cell contains a JSON array of ordered gallery URLs. Exact map
coordinates are stored separately in `latitude` and `longitude` (WGS84). These
values come from the same structured `gps` payload used by the site's MapLibre
marker.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## Configure

Import a search URL and optionally override its price range:

```bash
python3 -m src.cli --url 'https://www.bezrealitky.com/search?estateType=BYT&offerType=PRONAJEM' --price_from 750 --price_to 1200
```

`--url` also accepts a Markdown link copied from a chat message. Only HTTPS
Bezrealitky `/search` URLs are accepted. Repeated query parameters such as
`disposition` are preserved.

Show the current config or restore the immutable defaults:

```bash
python3 -m src.cli --show
python3 -m src.cli --reset
```

The active settings live in `config/config.yaml`; defaults are kept separately
in `config/defaults.yaml`.

## Run

```bash
python3 -m src.run_pipeline
```

You can update the config and run immediately:

```bash
python3 -m src.cli --price_from 750 --price_to 1200 --run
```

The default output is `output/bezrealitky_listings.csv`. A non-zero exit code
means that one or more discovered publications could not be fetched or parsed;
successfully parsed rows are still saved.

## Docker

Build the image:

```bash
docker compose build
```

The container entrypoint is the same CLI. The Compose service mounts `config/`
and `output/`, so config updates and generated CSV files persist on the host:

```bash
docker compose run --rm scraper --show
docker compose run --rm scraper --price_from 750 --price_to 1200
docker compose run --rm scraper --url 'https://www.bezrealitky.com/search?estateType=BYT&offerType=PRONAJEM'
docker compose run --rm scraper --reset
docker compose run --rm scraper --run
```

Without Compose:

```bash
docker build -t bezrealitky-parser .
docker run --rm \
  -v "$PWD/config:/app/config" \
  -v "$PWD/output:/app/output" \
  bezrealitky-parser --run
```

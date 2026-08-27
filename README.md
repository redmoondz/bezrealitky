# Bezrealitky CSV parser

The parser reads every page of a Bezrealitky search, deduplicates publication
links, opens every publication, and writes the normalized data to CSV.

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

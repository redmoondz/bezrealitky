"""Run the scraper with config/config.yaml."""

try:
    from .scraper import main
except ImportError:  # Support: python3 src/run_pipeline.py
    from scraper import main


if __name__ == "__main__":
    raise SystemExit(main())

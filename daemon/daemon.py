import time
import yaml
import logging
from pathlib import Path

from .watcher import WorkflowWatcher
from .model_resolver import ModelResolver
from .downloader import ModelDownloader


def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with config_path.open("r") as f:
        return yaml.safe_load(f)


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s] [%(levelname)s] %(message)s",
    )


def main():
    config = load_config()
    setup_logging(config.get("logging", {}).get("level", "INFO"))

    logging.info("Loading daemon configuration")

    resolver = ModelResolver(config["model_sources"])
    downloader = ModelDownloader(
        retries=config["download"]["retries"],
        backoff=config["download"]["backoff_seconds"],
        timeout=config["download"]["timeout_seconds"],
    )

    watcher = WorkflowWatcher(
        directories=config["watch_directories"],
        resolver=resolver,
        downloader=downloader,
        models_dir=config["models_directory"],
        input_dir=config["input_directory"],
    )

    logging.info("Daemon initialized. Watching for workflow changes.")

    try:
        while True:
            watcher.poll()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Daemon shutting down.")


if __name__ == "__main__":
    main()


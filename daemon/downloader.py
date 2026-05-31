import logging
import time
import requests
from pathlib import Path


class ModelDownloader:
    """
    Downloads model files into the cache directory.
    Ensures atomic writes and retry/backoff behavior.
    """

    def __init__(self, cache_dir: Path, retries: int, backoff: int, timeout: int):
        self.cache_dir = cache_dir

        self.retries = retries
        self.backoff = backoff
        self.timeout = timeout

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Model cache directory: {self.cache_dir}")

    def ensure_present(self, target: Path, url: str):
        """
        Ensure the model file exists at *target*.
        If missing, download it from *url*.
        """
        if target.exists():
            logging.debug(f"Model already exists: {target}")
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f"Downloading {target.name} from {url}")
        self._download_with_retries(url, target)

    def _download_with_retries(self, url: str, target: Path):
        """
        Download with retry/backoff logic.
        Writes to a temporary file first, then renames atomically.
        """
        tmp_path = target.with_suffix(".tmp")

        for attempt in range(1, self.retries + 1):
            try:
                self._download(url, tmp_path)
                tmp_path.rename(target)
                logging.info(f"Downloaded model to {target}")
                return
            except Exception as e:
                logging.warning(
                    f"Download failed (attempt {attempt}/{self.retries}): {e}"
                )
                if attempt < self.retries:
                    time.sleep(self.backoff)

        logging.error(f"Failed to download model after {self.retries} attempts")

    def _download(self, url: str, tmp_path: Path):
        """
        Perform the actual HTTP GET and stream to disk.
        """
        with requests.get(url, stream=True, timeout=self.timeout) as r:
            r.raise_for_status()

            with tmp_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

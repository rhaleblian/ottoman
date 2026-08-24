import logging
import time
import requests
from pathlib import Path


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_rate(n: float) -> str:
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB/s"


class ModelDownloader:
    """
    Downloads model files to the models directory.
    Ensures atomic writes and retry/backoff behavior.
    """

    def __init__(self, retries: int, backoff: int, timeout: int):
        self.retries = retries
        self.backoff = backoff
        self.timeout = timeout

        self._total_bytes = 0
        self._total_time = 0.0

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
                bytes_written, elapsed = self._download(url, tmp_path)
                tmp_path.rename(target)

                rate = bytes_written / elapsed if elapsed > 0 else 0.0
                self._total_bytes += bytes_written
                self._total_time += elapsed
                avg_rate = (
                    self._total_bytes / self._total_time
                    if self._total_time > 0
                    else 0.0
                )

                logging.info(
                    f"Downloaded {_fmt_size(bytes_written)} to {target} "
                    f"in {elapsed:.2f}s ({_fmt_rate(rate)} — "
                    f"running avg {_fmt_rate(avg_rate)})"
                )
                return
            except Exception as e:
                logging.warning(
                    f"Download failed (attempt {attempt}/{self.retries}): {e}"
                )
                if attempt < self.retries:
                    time.sleep(self.backoff)

        logging.error(f"Failed to download model after {self.retries} attempts")

    def _download(self, url: str, tmp_path: Path) -> tuple[int, float]:
        """
        Perform the actual HTTP GET and stream to disk.
        Returns (bytes_written, elapsed_seconds).
        """
        start = time.time()
        total = 0
        with requests.get(url, stream=True, timeout=self.timeout) as r:
            r.raise_for_status()

            with tmp_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
        elapsed = time.time() - start
        return (total, elapsed)

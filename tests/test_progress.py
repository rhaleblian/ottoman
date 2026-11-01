import io
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from daemon.downloader import ModelDownloader
from daemon.workflow_models import _download_file, _download_input_file


class _FakeRequestsResponse:
    def __init__(self, chunks: list[bytes], headers: dict[str, str] | None = None):
        self._chunks = chunks
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size: int = 8192):
        yield from self._chunks


class _FakeUrlopenResponse:
    def __init__(
        self,
        chunks: list[bytes],
        headers: dict[str, str] | None = None,
        status: int = 200,
    ):
        self._chunks = list(chunks)
        self.headers = headers or {}
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class TestDownloadProgress(unittest.TestCase):
    def _capture_logger_stderr(self) -> tuple[io.StringIO, logging.Handler, int]:
        buf = io.StringIO()
        root = logging.getLogger()
        prev_level = root.level
        root.setLevel(logging.INFO)
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root.addHandler(handler)
        return buf, handler, prev_level

    def _restore_logger(self, handler: logging.Handler, prev_level: int) -> None:
        root = logging.getLogger()
        root.removeHandler(handler)
        root.setLevel(prev_level)

    def test_model_downloader_10_percent_intervals(self):
        # 20 chunks of 50 bytes = 1000 bytes (5% per chunk -> hits every 10%)
        chunks = [b"x" * 50 for _ in range(20)]
        fake_resp = _FakeRequestsResponse(chunks, headers={"Content-Length": "1000"})

        buf, handler, prev_level = self._capture_logger_stderr()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                downloader = ModelDownloader(
                    cache_dir=tmp_path / "cache", retries=1, backoff=0, timeout=5
                )
                target = tmp_path / "models" / "test_model.safetensors"
                with patch("daemon.downloader.requests.get", return_value=fake_resp):
                    downloader.ensure_present(target, "https://example.com/model")

                self.assertTrue(target.exists())
                self.assertEqual(target.stat().st_size, 1000)
        finally:
            self._restore_logger(handler, prev_level)

        progress_lines = [
            line
            for line in buf.getvalue().splitlines()
            if "Downloading test_model.safetensors:" in line
        ]
        expected_milestones = [f"{pct}%" for pct in range(10, 101, 10)]
        actual_milestones = [
            line.split("Downloading test_model.safetensors: ")[1].split(" ")[0]
            for line in progress_lines
        ]
        self.assertEqual(actual_milestones, expected_milestones)

    def test_model_downloader_missing_content_length_and_overflow_guard(self):
        # Without Content-Length: downloads cleanly with no percentage lines
        chunks = [b"a" * 100 for _ in range(5)]
        fake_no_cl = _FakeRequestsResponse(chunks, headers={})

        buf, handler, prev_level = self._capture_logger_stderr()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                downloader = ModelDownloader(
                    cache_dir=tmp_path / "cache", retries=1, backoff=0, timeout=5
                )
                target1 = tmp_path / "no_cl.safetensors"
                with patch("daemon.downloader.requests.get", return_value=fake_no_cl):
                    downloader.ensure_present(target1, "https://example.com/m1")

                # Overflow beyond Content-Length should never exceed or repeat 100%
                overflow_chunks = [b"b" * 100 for _ in range(12)]
                fake_overflow = _FakeRequestsResponse(
                    overflow_chunks, headers={"Content-Length": "1000"}
                )
                target2 = tmp_path / "overflow.safetensors"
                with patch(
                    "daemon.downloader.requests.get", return_value=fake_overflow
                ):
                    downloader.ensure_present(target2, "https://example.com/m2")
        finally:
            self._restore_logger(handler, prev_level)

        lines = buf.getvalue().splitlines()
        self.assertEqual(
            [ln for ln in lines if "Downloading no_cl.safetensors:" in ln], []
        )
        overflow_milestones = [
            ln.split("Downloading overflow.safetensors: ")[1].split(" ")[0]
            for ln in lines
            if "Downloading overflow.safetensors:" in ln
        ]
        self.assertEqual(
            overflow_milestones, [f"{pct}%" for pct in range(10, 101, 10)]
        )

    def test_workflow_models_download_file_and_resume_intervals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dest = tmp_path / "flux.safetensors"
            chunks = [b"x" * 100 for _ in range(10)]
            fake_resp = _FakeUrlopenResponse(
                chunks, headers={"Content-Length": "1000"}, status=200
            )
            stderr_buf = io.StringIO()
            with (
                patch("urllib.request.urlopen", return_value=fake_resp),
                patch("sys.stderr", stderr_buf),
            ):
                status, size, _ = _download_file("https://example.com/flux", dest)

            self.assertEqual(status, "downloaded")
            self.assertEqual(size, 1000)
            milestones = [
                ln.strip().split(": ")[1].split(" ")[0]
                for ln in stderr_buf.getvalue().splitlines()
                if "flux.safetensors:" in ln
            ]
            self.assertEqual(milestones, [f"{pct}%" for pct in range(10, 101, 10)])

            # Resumed download starting at 350 / 1000 bytes (35%) -> 40%..100%
            dest_resumed = tmp_path / "resumed.safetensors"
            part = dest_resumed.with_suffix(".safetensors.part")
            part.write_bytes(b"r" * 350)
            resume_chunks = [
                b"r" * 50,
                *[b"r" * 100 for _ in range(6)],
            ]
            fake_resume_resp = _FakeUrlopenResponse(
                resume_chunks,
                headers={"Content-Range": "bytes 350-999/1000"},
                status=206,
            )
            resume_buf = io.StringIO()
            with (
                patch("urllib.request.urlopen", return_value=fake_resume_resp),
                patch("sys.stderr", resume_buf),
            ):
                status, size, _ = _download_file(
                    "https://example.com/resumed", dest_resumed
                )

            self.assertEqual(status, "resumed")
            self.assertEqual(size, 1000)
            resumed_milestones = [
                ln.strip().split(": ")[1].split(" ")[0]
                for ln in resume_buf.getvalue().splitlines()
                if "resumed.safetensors:" in ln
            ]
            self.assertEqual(
                resumed_milestones, [f"{pct}%" for pct in range(40, 101, 10)]
            )

    def test_download_input_file_10_percent_intervals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "clip.mp4"
            chunks = [b"v" * 100 for _ in range(10)]
            fake_resp = _FakeUrlopenResponse(
                chunks, headers={"Content-Length": "1000"}, status=200
            )
            stderr_buf = io.StringIO()
            with (
                patch("urllib.request.urlopen", return_value=fake_resp),
                patch("sys.stderr", stderr_buf),
            ):
                status = _download_input_file("clip.mp4", dest)

            self.assertEqual(status, "downloaded")
            milestones = [
                ln.strip().split(": ")[1].split(" ")[0]
                for ln in stderr_buf.getvalue().splitlines()
                if "clip.mp4:" in ln
            ]
            self.assertEqual(milestones, [f"{pct}%" for pct in range(10, 101, 10)])


if __name__ == "__main__":
    unittest.main()

import json
import logging
import sys
from pathlib import Path
from typing import List

from .workflow_models import get_workflow_models


class WorkflowWatcher:
    """
    Polls workflow directories for JSON workflow files.
    When a workflow changes, it extracts required models,
    resolves them to URLs, and triggers downloads.
    """

    def __init__(self, directories: List[str], resolver, downloader, state, models_dir: str):
        self.directories = [Path(d) for d in directories]
        self.resolver = resolver
        self.downloader = downloader
        self.state = state
        self.models_dir = Path(models_dir)

        for d in self.directories:
            d.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        logging.info(f"Watching {len(self.directories)} workflow directories")

    def poll(self):
        """
        Called once per main-loop tick.
        Scans workflow directories for JSON files and processes any that changed.
        """
        for directory in self.directories:
            for file in directory.glob("*.json"):
                self._process_workflow(file)

    def _process_workflow(self, path: Path):
        """
        If the workflow file changed since last seen, parse it and handle models.
        """
        mtime = path.stat().st_mtime

        if not self.state.should_process(path, mtime):
            return

        logging.info(f"Detected workflow change: {path}")

        try:
            with path.open("r") as f:
                workflow = json.load(f)
        except Exception as e:
            logging.error(f"Failed to parse workflow {path}: {e}")
            return

        refs = get_workflow_models(workflow)

        for ref in refs:
            print(f"  {ref}", file=sys.stderr)

        logging.info(f"Workflow requires {len(refs)} models")

        for ref in refs:
            url = ref.url
            if not url:
                url = self.resolver.resolve(ref.name)
            if not url:
                logging.warning(f"No source found for model: {ref.directory}/{ref.name}")
                continue

            target = self.models_dir / ref.directory / ref.name
            self.downloader.ensure_present(target, url)

        self.state.mark_processed(path, mtime)

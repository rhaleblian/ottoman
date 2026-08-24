import json
import logging
from pathlib import Path
from typing import List

from .workflow_models import get_workflow_models, get_workflow_inputs, download_workflow_inputs


class WorkflowWatcher:
    """
    Polls workflow directories for JSON workflow files.
    When a workflow changes, it extracts required models,
    resolves them to URLs, and triggers downloads.
    """

    def __init__(self, directories: List[str], resolver, downloader,
                 models_dir: str, input_dir: str):
        self.directories = [Path(d) for d in directories]
        self.resolver = resolver
        self.downloader = downloader
        self.models_dir = Path(models_dir)
        self.input_dir = Path(input_dir)

        for d in self.directories:
            d.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)

        logging.info(f"Watching {len(self.directories)} workflow directories")

        for d in self.directories:
            workflows = sorted(d.glob("*.json"))
            if workflows:
                logging.info(f"Found {len(workflows)} workflow(s) in {d}:")
                for wf in workflows:
                    logging.info(f"  {wf.name}")
            else:
                logging.info(f"No workflow files found in {d}")

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
        Parse a workflow file and ensure all required models and inputs are present.
        """
        try:
            with path.open("r") as f:
                workflow = json.load(f)
        except Exception as e:
            logging.error(f"Failed to parse workflow {path}: {e}")
            return

        refs = get_workflow_models(workflow)

        for ref in refs:
            url = ref.url
            if not url:
                url = self.resolver.resolve(ref.name)
            if not url:
                logging.warning(f"No source found for model: {ref.directory}/{ref.name}")
                continue

            target = self.models_dir / ref.directory / ref.name
            self.downloader.ensure_present(target, url)

        inputs = get_workflow_inputs(workflow)
        if inputs:
            download_workflow_inputs(workflow, self.input_dir)

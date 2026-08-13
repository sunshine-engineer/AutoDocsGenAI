from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TextIO


class ProgressReporter:
    """Render concise, human-readable pipeline progress to a text stream."""

    def __init__(self, output: TextIO | None = None) -> None:
        self.output = output or sys.stdout

    def completed(
        self,
        stage: str,
        metadata: Mapping[str, object],
        artifact: str | Path | None = None,
    ) -> None:
        """Print a completed stage with counts and an optional artifact path."""

        print(f"\n[COMPLETED] {stage}", file=self.output)
        for key, value in metadata.items():
            label = key.replace("_", " ").capitalize()
            print(f"  {label}: {value}", file=self.output)
        if artifact is not None:
            print(f"  Saved at: {Path(artifact).resolve()}", file=self.output)

    def next_stage(self, stage: str) -> None:
        """Make the current implementation boundary explicit."""

        print(f"\n[NEXT] {stage}", file=self.output)

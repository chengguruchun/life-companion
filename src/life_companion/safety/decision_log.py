"""Append-only decision log (JSONL)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator, Optional

from life_companion.models.safety import DecisionRecord


class DecisionLog:
    """Append-only store for DecisionRecord rows."""

    def __init__(self, path: Optional[str | Path] = None) -> None:
        if path is None:
            base = Path(os.environ.get("LIFE_COMPANION_DATA_DIR", "data")).expanduser()
            path = base / "decisions.jsonl"
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: DecisionRecord) -> DecisionRecord:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
        return record

    def read_all(self) -> list[DecisionRecord]:
        if not self.path.exists():
            return []
        rows: list[DecisionRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(DecisionRecord.model_validate_json(line))
        return rows

    def iter_records(self) -> Iterator[DecisionRecord]:
        yield from self.read_all()

    def find_by_proposal(self, proposal_id: str) -> list[DecisionRecord]:
        return [r for r in self.read_all() if r.proposal_id == proposal_id]

    def find_by_id(self, decision_id: str) -> Optional[DecisionRecord]:
        for r in self.read_all():
            if r.decision_id == decision_id:
                return r
        return None

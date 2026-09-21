"""Local JSON persistence for goal tree + preference memory under data/."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from life_companion.models.goals import GoalTree
from life_companion.models.outcome import GapReport, Outcome
from life_companion.models.proposal import PreferenceWrite
from life_companion.models.safety import DecisionRecord


class LocalStore:
    def __init__(self, data_dir: Optional[str | Path] = None) -> None:
        raw = data_dir or os.environ.get("LIFE_COMPANION_DATA_DIR", "data")
        self.data_dir = Path(raw).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.goals_path = self.data_dir / "goals.json"
        self.prefs_path = self.data_dir / "preferences.json"
        self.audit_path = self.data_dir / "critic_overrides.jsonl"
        self.outcomes_path = self.data_dir / "outcomes.jsonl"
        self.gaps_path = self.data_dir / "gap_reports.jsonl"
        self.decisions_path = self.data_dir / "decisions.jsonl"

    def load_goals(self) -> GoalTree:
        if not self.goals_path.exists():
            return GoalTree()
        return GoalTree.model_validate_json(self.goals_path.read_text(encoding="utf-8"))

    def save_goals(self, tree: GoalTree) -> None:
        self.goals_path.write_text(
            tree.model_dump_json(indent=2), encoding="utf-8"
        )

    def load_preferences(self) -> dict[str, Any]:
        if not self.prefs_path.exists():
            return {}
        return json.loads(self.prefs_path.read_text(encoding="utf-8"))

    def save_preferences(self, prefs: dict[str, Any]) -> None:
        self.prefs_path.write_text(
            json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def apply_preference_writes(
        self, writes: list[PreferenceWrite], *, require_confirm: bool = False
    ) -> dict[str, Any]:
        """Merge preference writes. Important prefs may need user confirm (caller)."""
        prefs = self.load_preferences()
        applied: dict[str, Any] = {}
        for w in writes:
            if require_confirm and w.confidence < 0.8:
                continue
            prefs[w.key] = {
                "value": w.value,
                "confidence": w.confidence,
                "rationale": w.rationale,
            }
            applied[w.key] = w.value
        self.save_preferences(prefs)
        return applied

    def log_critic_override(self, proposal_id: str, reason: str) -> None:
        entry = {"proposal_id": proposal_id, "reason": reason}
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # --- v0.2 outcomes / gaps ---

    def save_outcome(self, outcome: Outcome) -> None:
        """Append outcome to outcomes.jsonl."""
        with self.outcomes_path.open("a", encoding="utf-8") as f:
            f.write(outcome.model_dump_json() + "\n")

    def load_outcomes(self) -> list[Outcome]:
        if not self.outcomes_path.exists():
            return []
        rows: list[Outcome] = []
        for line in self.outcomes_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(Outcome.model_validate_json(line))
        return rows

    def save_gap_report(self, report: GapReport) -> None:
        with self.gaps_path.open("a", encoding="utf-8") as f:
            f.write(report.model_dump_json() + "\n")

    def load_gap_reports(self) -> list[GapReport]:
        if not self.gaps_path.exists():
            return []
        rows: list[GapReport] = []
        for line in self.gaps_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(GapReport.model_validate_json(line))
        return rows

    # --- v0.3 decisions ---

    def save_decision(self, record: DecisionRecord) -> DecisionRecord:
        with self.decisions_path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
        return record

    def load_decisions(self) -> list[DecisionRecord]:
        if not self.decisions_path.exists():
            return []
        rows: list[DecisionRecord] = []
        for line in self.decisions_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(DecisionRecord.model_validate_json(line))
        return rows

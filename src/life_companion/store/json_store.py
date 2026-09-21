"""Local JSON persistence for goal tree + preference memory under data/."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from life_companion.models.goals import GoalTree
from life_companion.models.proposal import PreferenceWrite


class LocalStore:
    def __init__(self, data_dir: Optional[str | Path] = None) -> None:
        raw = data_dir or os.environ.get("LIFE_COMPANION_DATA_DIR", "data")
        self.data_dir = Path(raw).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.goals_path = self.data_dir / "goals.json"
        self.prefs_path = self.data_dir / "preferences.json"
        self.audit_path = self.data_dir / "critic_overrides.jsonl"

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

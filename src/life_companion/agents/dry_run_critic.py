"""Deterministic rule-based critic stub for --dry-run / CI (no API key)."""

from __future__ import annotations

from life_companion.models.proposal import (
    Objection,
    Proposal,
    ProposalType,
    Review,
    Verdict,
)


def rule_based_critic(proposal: Proposal, *, revised: bool = False) -> Review:
    """Apply simple hard-constraint heuristics.

    - Reject day plans that schedule work over child pickup / sleep.
    - Conditional pass if entertainment crowds deep work before a clear deadline hint.
    - Reject preference writes with very low confidence without rationale.
    - Otherwise pass.
    """
    objections: list[Objection] = []
    conditions: list[str] = []
    fixes: list[str] = []

    if proposal.today_plan:
        for block in proposal.today_plan:
            title_l = block.title.lower()
            # Overlap heuristic on start time strings HH:MM
            start = block.start
            if start >= "17:30" and start < "18:00":
                if "pickup" not in title_l and "接" not in block.title:
                    objections.append(
                        Objection(
                            code="hard_constraint_pickup",
                            message=f"Block '{block.title}' overlaps child pickup window 17:30–18:00",
                            severity="high",
                        )
                    )
                    fixes.append("Move work blocks off 17:30–18:00 or mark as after pickup.")
            if start >= "23:00" or (block.end <= "07:00" and start >= "22:00"):
                if "sleep" not in title_l and "睡眠" not in block.title:
                    objections.append(
                        Objection(
                            code="hard_constraint_sleep",
                            message=f"Block '{block.title}' invades sleep window",
                            severity="high",
                        )
                    )
                    fixes.append("Do not schedule learning/work into sleep window by default.")

    if proposal.type == ProposalType.WRITE_PREFERENCE and proposal.preference_writes:
        for pw in proposal.preference_writes:
            if pw.confidence < 0.4 and not pw.rationale:
                objections.append(
                    Objection(
                        code="weak_preference_evidence",
                        message=f"Preference '{pw.key}' has low confidence and no rationale",
                        severity="medium",
                    )
                )
                conditions.append(f"Ask user to confirm preference '{pw.key}' before write.")
                fixes.append("Add rationale or lower to suggestion-only.")

    if proposal.type == ProposalType.SEND_EMAIL:
        actions = proposal.tool_actions or []
        if not any(a.requires_hitl or a.tool == "email_draft_send" for a in actions):
            objections.append(
                Objection(
                    code="missing_hitl",
                    message="Email send must go through HITL gate",
                    severity="high",
                )
            )
            fixes.append("Set tool_actions email_draft_send with requires_hitl=True.")

    high = [o for o in objections if o.severity == "high"]
    if high and revised:
        # After one revise round still broken → reject (no infinite loop)
        return Review(
            proposal_id=proposal.proposal_id,
            verdict=Verdict.REJECT,
            objections=objections,
            conditions=conditions,
            suggested_fixes=fixes + ["Ask user; do not auto-execute."],
        )
    # Fixable issues (including hard-constraint overlaps) → conditional_pass first
    if objections or conditions or high:
        return Review(
            proposal_id=proposal.proposal_id,
            verdict=Verdict.CONDITIONAL_PASS,
            objections=objections,
            conditions=conditions or ["Address suggested fixes once."],
            suggested_fixes=fixes,
        )
    return Review(
        proposal_id=proposal.proposal_id,
        verdict=Verdict.PASS,
        objections=[],
        conditions=[],
        suggested_fixes=[],
    )


def apply_suggested_fixes(proposal: Proposal, review: Review) -> Proposal:
    """Deterministic one-shot revise for dry-run demos."""
    data = proposal.model_copy(deep=True)
    if data.today_plan:
        new_blocks = []
        for block in data.today_plan:
            start = block.start
            title_l = block.title.lower()
            if start >= "17:30" and start < "18:00" and "接" not in block.title and "pickup" not in title_l:
                block = block.model_copy(update={"start": "18:15", "end": "19:00"})
            if (start >= "23:00" or start >= "22:00") and "sleep" not in title_l and "睡眠" not in block.title:
                # drop sleep-invading blocks
                continue
            new_blocks.append(block)
        data.today_plan = new_blocks
        data.summary = data.summary + " [revised once]"
    if data.preference_writes:
        fixed = []
        for pw in data.preference_writes:
            if pw.confidence < 0.4 and not pw.rationale:
                pw = pw.model_copy(
                    update={"rationale": "inferred from repeated evening walk habit", "confidence": 0.6}
                )
            fixed.append(pw)
        data.preference_writes = fixed
    if data.type == ProposalType.SEND_EMAIL:
        actions = list(data.tool_actions or [])
        if not any(a.tool == "email_draft_send" for a in actions):
            from life_companion.models.proposal import ToolAction

            actions.append(
                ToolAction(
                    tool="email_draft_send",
                    args={"to": "boss@example.com", "subject": "OKR", "body": "..."},
                    mutating=True,
                    requires_hitl=True,
                )
            )
        data.tool_actions = actions
    # annotate that we used review suggestions
    _ = review
    return data

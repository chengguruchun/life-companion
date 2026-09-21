"""MVP stub tools with clear interfaces. NOT real integrations."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def _stub(name: str, **payload: Any) -> dict[str, Any]:
    return {"_stub": True, "tool": name, **payload}


def calendar_list_events(day: str | None = None) -> dict[str, Any]:
    """STUB: list calendar events for a day (YYYY-MM-DD)."""
    d = day or date.today().isoformat()
    return _stub(
        "calendar_list_events",
        day=d,
        events=[
            {
                "id": "evt-sleep",
                "title": "Sleep window",
                "start": f"{d}T23:00:00",
                "end": f"{(date.fromisoformat(d) + timedelta(days=1)).isoformat()}T07:00:00",
                "hard": True,
            },
            {
                "id": "evt-pickup",
                "title": "Child pickup",
                "start": f"{d}T17:30:00",
                "end": f"{d}T18:00:00",
                "hard": True,
            },
            {
                "id": "evt-standup",
                "title": "Team standup",
                "start": f"{d}T10:00:00",
                "end": f"{d}T10:30:00",
                "hard": False,
            },
        ],
    )


def calendar_free_slots(day: str | None = None, min_minutes: int = 30) -> dict[str, Any]:
    """STUB: return free slots after subtracting hard events."""
    d = day or date.today().isoformat()
    return _stub(
        "calendar_free_slots",
        day=d,
        min_minutes=min_minutes,
        slots=[
            {"start": f"{d}T08:00:00", "end": f"{d}T09:45:00"},
            {"start": f"{d}T10:30:00", "end": f"{d}T12:00:00"},
            {"start": f"{d}T13:30:00", "end": f"{d}T17:00:00"},
            {"start": f"{d}T19:00:00", "end": f"{d}T21:30:00"},
        ],
    )


def calendar_upsert_event(
    title: str, start: str, end: str, *, hard: bool = False
) -> dict[str, Any]:
    """STUB: write calendar event (mutating)."""
    return _stub(
        "calendar_upsert_event",
        title=title,
        start=start,
        end=end,
        hard=hard,
        status="accepted_stub",
    )


def weather_forecast(city: str = "Hangzhou", day: str | None = None) -> dict[str, Any]:
    """STUB: weather forecast."""
    return _stub(
        "weather_forecast",
        city=city,
        day=day or date.today().isoformat(),
        summary="多云，气温 18–26°C，降水概率 20%",
        rain_likely=False,
    )


def traffic_eta(origin: str, destination: str, depart_at: str | None = None) -> dict[str, Any]:
    """STUB: traffic / ETA."""
    return _stub(
        "traffic_eta",
        origin=origin,
        destination=destination,
        depart_at=depart_at or datetime.now().isoformat(timespec="minutes"),
        eta_minutes=35,
        congestion="moderate",
    )


def email_list(limit: int = 5) -> dict[str, Any]:
    """STUB: list recent emails (read-only)."""
    return _stub(
        "email_list",
        emails=[
            {
                "id": "m1",
                "from": "boss@example.com",
                "subject": "Q3 OKR draft",
                "snippet": "Please review by Friday",
            }
        ][:limit],
    )


def email_draft_send(
    to: str, subject: str, body: str, *, approved: bool = False
) -> dict[str, Any]:
    """STUB: send email — REQUIRES HITL. Never sends without approved=True."""
    if not approved:
        return _stub(
            "email_draft_send",
            status="pending_hitl",
            to=to,
            subject=subject,
            body_preview=body[:200],
            message="Email send blocked until human approval (HITL).",
        )
    return _stub(
        "email_draft_send",
        status="sent_stub",
        to=to,
        subject=subject,
    )


def wiki_lookup(query: str) -> dict[str, Any]:
    """STUB: personal wiki / knowledge base lookup."""
    return _stub(
        "wiki_lookup",
        query=query,
        hits=[{"title": f"(stub) Notes about {query}", "snippet": "No real wiki wired yet."}],
    )


def web_search(query: str, max_results: int = 3) -> dict[str, Any]:
    """STUB: web search."""
    return _stub(
        "web_search",
        query=query,
        results=[
            {
                "title": f"(stub) Result for {query}",
                "url": "https://example.com/stub",
                "snippet": "Replace with real search provider later.",
            }
        ][:max_results],
    )


# Callable registry for agent wiring / CLI demos
STUB_TOOLS = {
    "calendar_list_events": calendar_list_events,
    "calendar_free_slots": calendar_free_slots,
    "calendar_upsert_event": calendar_upsert_event,
    "weather_forecast": weather_forecast,
    "traffic_eta": traffic_eta,
    "email_list": email_list,
    "email_draft_send": email_draft_send,
    "wiki_lookup": wiki_lookup,
    "web_search": web_search,
}

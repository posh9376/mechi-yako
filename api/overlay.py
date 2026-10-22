"""Timed overlay JSON a graphics layer can place on a live feed."""

from __future__ import annotations

from typing import Any

from pipeline.replay import MatchReplay
from pipeline.state import MatchStateAggregator

OVERLAY_SCHEMA = "mechi-yako-overlay-v1"

# Distinct roles in the claim-then-verify chain. Overlay is the render step;
# persona rewrite happens after this payload, so Personalize is listed last.
PIPELINE = (
    {"id": "ingest", "role": "Ingest", "agent": "MatchReplay"},
    {"id": "detector", "role": "Interpret", "agent": "MomentDetector"},
    {"id": "explainer", "role": "Explain", "agent": "Explainer"},
    {"id": "verifier", "role": "Verify", "agent": "Verifier"},
    {"id": "render", "role": "Render", "agent": "Overlay"},
    {"id": "persona", "role": "Personalize", "agent": "PersonaWriter"},
)


def overlay_for_moment(match_id: str, moment: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    clock = moment["t_peak"]
    events = MatchReplay(doc, instant=True, end_clock=clock).events
    agg = MatchStateAggregator(doc["match"])
    agg.ingest_all(events)
    state = agg.snapshot()
    home, away = state["score"]
    headline = dict(moment.get("headline") or {})
    return {
        "schema": OVERLAY_SCHEMA,
        "match_id": match_id,
        "t": clock,
        "period": state["period"],
        "score": {"home": home, "away": away},
        "team": moment["team"],
        "moment_type": moment["type"],
        "moment_id": moment["id"],
        "event_ids": list(moment["event_ids"]),
        "headline": headline,
        "text": headline.get("en") or moment["type"],
        "stats": dict(moment.get("stats") or {}),
        "pipeline": list(PIPELINE),
    }

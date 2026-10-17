"""Write demo match JSON, fact-layer fixtures, and print realism report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generator.realism import format_report, report_passed, run_realism_report
from generator.scripted_demo import MATCH_ID, build_demo_match, build_demo_match_public

MATCHES = ROOT / "data" / "matches"
FIXTURES = ROOT / "data" / "fixtures"


def build_fixtures(full: dict) -> dict:
    planted = full["_planted"]
    turnover_ids = planted["turnover_event_ids"]
    pressure_ids = planted["pressure_event_ids"]

    moments = [
        {
            "id": "mom-pressure-01",
            "match_id": MATCH_ID,
            "type": "pressure_spell",
            "t_start": "55:05",
            "t_end": "61:45",
            "t_peak": "58:55",
            "team": "RK",
            "headline": {
                "en": "Red Kites pressed high and forced repeated turnovers in the Blue Herons half."
            },
            "significance": 0.86,
            "event_ids": pressure_ids + turnover_ids,
            "stats": {
                "high_turnovers": len(turnover_ids),
                "pressure_events": len([e for e in pressure_ids if e.startswith("e-")]),
                "window_minutes": 7,
                "zone": "BH_own_half",
            },
            "entities": {"team": "RK", "opponent": "BH", "key_player": "RK-4"},
        },
        {
            "id": "mom-shot-after-turnovers-01",
            "match_id": MATCH_ID,
            "type": "shot_after_turnovers",
            "t_start": "55:18",
            "t_end": "60:19",
            "t_peak": "60:18",
            "team": "RK",
            "headline": {
                "en": "After several won tackles in the Blue Herons half, Red Kites created a shot."
            },
            "significance": 0.78,
            "event_ids": turnover_ids[:4] + [planted["shot_after_turnovers"]],
            "stats": {
                "turnovers_before_shot": 4,
                "shot_event_id": planted["shot_after_turnovers"],
                "shot_outcome": "saved",
            },
            "entities": {"team": "RK", "shooter": "RK-9"},
        },
        {
            "id": "mom-momentum-01",
            "match_id": MATCH_ID,
            "type": "momentum_swing",
            "t_start": "55:05",
            "t_end": "63:03",
            "t_peak": "63:02",
            "team": "RK",
            "headline": {
                "en": "The press flipped the half: Red Kites went from chasing to level."
            },
            "significance": 0.9,
            "event_ids": turnover_ids + [planted["equaliser"]],
            "stats": {
                "score_before": [1, 0],
                "score_after": [1, 1],
                "rk_turnovers_won": len(turnover_ids),
            },
            "entities": {"team": "RK", "opponent": "BH"},
        },
        {
            "id": "mom-goal-equaliser-01",
            "match_id": MATCH_ID,
            "type": "goal",
            "t_start": "62:48",
            "t_end": "63:03",
            "t_peak": "63:02",
            "team": "RK",
            "headline": {
                "en": "Omar Diallo equalised for Red Kites in the 63rd minute."
            },
            "significance": 0.95,
            "event_ids": [planted["equaliser"]],
            "stats": {
                "score_after": [1, 1],
                "scorer": "RK-9",
                "minute": 63,
            },
            "entities": {"scorer": "RK-9", "team": "RK"},
        },
        {
            "id": "mom-milestone-01",
            "match_id": MATCH_ID,
            "type": "player_milestone",
            "t_start": "55:18",
            "t_end": "78:14",
            "t_peak": "78:14",
            "team": "RK",
            "headline": {
                "en": "Makena Aoko won a fifth tackle, capping a relentless pressing shift."
            },
            "significance": 0.72,
            "event_ids": [],
            "stats": {
                "player": "RK-4",
                "metric": "tackles_won",
                "value": 5,
                "milestone": "5th_tackle_won",
            },
            "entities": {"player": "RK-4", "team": "RK"},
        },
    ]

    rk4_tackles = [
        e["id"]
        for e in full["events"]
        if e["type"] == "tackle"
        and e["player"] == "RK-4"
        and e.get("outcome") == "won_possession"
    ]
    moments[-1]["event_ids"] = rk4_tackles
    moments[-1]["stats"]["value"] = len(rk4_tackles)

    pressure_only = [eid for eid in pressure_ids if any(
        e["id"] == eid and e["type"] == "pressure" for e in full["events"]
    )]
    moments[0]["stats"]["pressure_events"] = len(pressure_only)
    moments[0]["stats"]["high_turnovers"] = len(turnover_ids)
    moments[0]["event_ids"] = list(dict.fromkeys(pressure_only + turnover_ids))

    return {
        "schema_version": "1.0",
        "match_id": MATCH_ID,
        "moments": moments,
    }


def main() -> int:
    MATCHES.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)

    full = build_demo_match()
    public = build_demo_match_public()
    fixtures = build_fixtures(full)

    match_path = MATCHES / f"{MATCH_ID}.json"
    fixture_path = FIXTURES / f"{MATCH_ID}.moments.json"

    match_path.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    fixture_path.write_text(json.dumps(fixtures, indent=2) + "\n", encoding="utf-8")

    results = run_realism_report(public)
    print(format_report(results))
    print(f"Wrote {match_path.relative_to(ROOT)} ({len(public['events'])} events)")
    print(f"Wrote {fixture_path.relative_to(ROOT)} ({len(fixtures['moments'])} moments)")

    return 0 if report_passed(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

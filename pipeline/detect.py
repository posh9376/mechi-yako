"""CLI: aggregate state + detect moments for a match file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.moments import MomentDetector
from pipeline.replay import load_match
from pipeline.state import MatchStateAggregator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATCH = ROOT / "data" / "matches" / "m-demo-001.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run state aggregator + moment detector")
    parser.add_argument("--match", type=Path, default=DEFAULT_MATCH)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write detected moments JSON",
    )
    args = parser.parse_args()

    doc = load_match(args.match)
    agg = MatchStateAggregator(doc["match"])
    agg.ingest_all(doc["events"])
    state = agg.snapshot()

    detector = MomentDetector(doc["match"])
    moments = detector.detect_all(doc["events"])
    types = sorted({m["type"] for m in moments})

    print(f"Match {state['match_id']}  score={state['score']}  events={state['events_seen']}")
    print(f"Possession: {state['possession']}")
    print(f"Detected {len(moments)} moments: {types}")
    for m in sorted(moments, key=lambda x: (-x["significance"], x["t_peak"])):
        print(
            f"  [{m['significance']:.2f}] {m['type']:<22} @{m['t_peak']:>5}  "
            f"{m['team']}  {m['headline']['en']}"
        )

    if args.json_out:
        payload = {
            "schema_version": "1.0",
            "match_id": doc["match"]["id"],
            "moments": moments,
            "final_state": state,
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.json_out}")

    required = {
        "pressure_spell",
        "shot_after_turnovers",
        "momentum_swing",
        "goal",
        "player_milestone",
    }
    missing = required - set(types)
    if missing:
        print(f"MISSING moment types: {sorted(missing)}")
        return 1
    print("All five moment types present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

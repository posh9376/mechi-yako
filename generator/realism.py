"""Pass/fail realism checks for a match document (schema v1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _clock_to_seconds(t: str) -> int:
    parts = t.split(":")
    if len(parts) != 2:
        raise ValueError(f"bad clock: {t}")
    return int(parts[0]) * 60 + int(parts[1])


def run_realism_report(doc: dict[str, Any]) -> list[CheckResult]:
    events = doc["events"]
    match = doc["match"]
    results: list[CheckResult] = []

    passes = [e for e in events if e["type"] == "pass"]
    complete = [e for e in passes if e.get("outcome") == "complete"]
    if passes:
        rate = len(complete) / len(passes)
        ok = 0.65 <= rate <= 0.92
        results.append(
            CheckResult(
                "pass_completion",
                ok,
                f"{len(complete)}/{len(passes)} = {rate:.1%} (expect 65–92%)",
            )
        )
    else:
        results.append(CheckResult("pass_completion", False, "no passes"))

    shots = [e for e in events if e["type"] == "shot"]
    n_shots = len(shots)
    ok_shots = 6 <= n_shots <= 30
    results.append(
        CheckResult(
            "shots_per_match",
            ok_shots,
            f"{n_shots} shots (expect 6–30)",
        )
    )

    # Possession proxy: share of pass+carry+shot events by team
    poss_types = {"pass", "carry", "shot", "tackle", "interception"}
    by_team: dict[str, int] = {}
    for e in events:
        if e["type"] in poss_types:
            by_team[e["team"]] = by_team.get(e["team"], 0) + 1
    total = sum(by_team.values()) or 1
    shares = {k: v / total for k, v in by_team.items()}
    ok_poss = all(0.35 <= s <= 0.65 for s in shares.values()) and len(shares) >= 2
    detail = ", ".join(f"{k}={s:.0%}" for k, s in sorted(shares.items()))
    results.append(
        CheckResult(
            "possession_spread",
            ok_poss,
            f"{detail} (each side 35–65% of in-play events)",
        )
    )

    times = [_clock_to_seconds(e["t"]) for e in events]
    duration_min = max((max(times) / 60.0), 1.0)
    epm = len(events) / duration_min
    # Scripted demos are sparser than a full broadcast feed; floor is 1.0/min.
    ok_epm = 1.0 <= epm <= 25.0
    results.append(
        CheckResult(
            "events_per_minute",
            ok_epm,
            f"{len(events)} events / {duration_min:.0f} min ≈ {epm:.1f}/min (expect 1.0–25)",
        )
    )

    ht = match.get("score_ht", [0, 0])
    ft = match.get("score_ft", [0, 0])
    goals = [e for e in shots if e.get("outcome") == "goal"]
    home, away = match["home"]["code"], match["away"]["code"]
    scored = {home: 0, away: 0}
    for g in goals:
        scored[g["team"]] = scored.get(g["team"], 0) + 1
    ok_score = scored.get(home, 0) == ft[0] and scored.get(away, 0) == ft[1]
    results.append(
        CheckResult(
            "score_matches_goals",
            ok_score,
            f"FT metadata {ft}, goals counted {[scored.get(home,0), scored.get(away,0)]}; HT={ht}",
        )
    )

    return results


def report_passed(results: list[CheckResult]) -> bool:
    return all(r.passed for r in results)


def format_report(results: list[CheckResult]) -> str:
    lines = ["Realism report", "-" * 40]
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"[{mark}] {r.name}: {r.detail}")
    lines.append("-" * 40)
    lines.append("OVERALL: " + ("PASS" if report_passed(results) else "FAIL"))
    return "\n".join(lines)

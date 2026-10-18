"""Claims seam: recompute fact-layer stats from raw events and keep an audit log.

Default checker is ``AgentsClaimChecker``, which wraps Daniel's ``agents.verifier.ClaimVerifier``
and falls back to ``DeterministicClaimChecker`` for API metrics the library does not cover yet
(e.g. ``window_minutes``, ``scorer``).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from agents.verifier import ClaimVerifier
from pipeline.clock import parse_clock

# Metrics handled by agents.verifier.ClaimVerifier
# Metrics verified by agents.verifier against cited event_ids.
# ``tackles_won`` stays on the deterministic checker: milestone claims use a
# match-scoped tally through t_peak, not only the cited event list.
_AGENTS_METRICS = frozenset(
    {
        "event_count",
        "high_turnovers",
        "pressure_events",
        "turnovers_before_shot",
        "shot_outcome",
        "goals",
        "score_after",
        "literal",
    }
)

# Descriptive stat keys that are labels, not claims.
CONTEXT_KEYS = frozenset({"zone", "player", "metric", "milestone"})
FLOAT_TOLERANCE = 0.5
_TURNOVER_TYPES = frozenset({"tackle", "interception"})


class Unverifiable(Exception):
    pass


@dataclass(frozen=True)
class Claim:
    moment_id: str
    metric: str
    value: Any
    event_ids: tuple[str, ...]


class ClaimChecker(Protocol):
    def check(self, claim: Claim, moment: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]: ...


def _clock(event: dict[str, Any]) -> int:
    return parse_clock(event["t"])


def _opponent(doc: dict[str, Any], team: str) -> str:
    home, away = doc["match"]["home"]["code"], doc["match"]["away"]["code"]
    return away if team == home else home


def _in_defensive_half(doc: dict[str, Any], defending_team: str, event: dict[str, Any]) -> bool:
    loc = event.get("location")
    if not loc:
        return True
    x = loc[0]
    return x < 50 if defending_team == doc["match"]["home"]["code"] else x >= 50


def _is_turnover_won(event: dict[str, Any], team: str) -> bool:
    return (
        event["type"] in _TURNOVER_TYPES
        and event.get("outcome") == "won_possession"
        and event["team"] == team
    )


def _goals_until(doc: dict[str, Any], clock_s: int, *, inclusive: bool) -> list[int]:
    home, away = doc["match"]["home"]["code"], doc["match"]["away"]["code"]
    score = [0, 0]
    for e in doc["events"]:
        if e["type"] != "shot" or e.get("outcome") != "goal":
            continue
        t = _clock(e)
        if t > clock_s or (not inclusive and t == clock_s):
            continue
        if e["team"] == home:
            score[0] += 1
        elif e["team"] == away:
            score[1] += 1
    return score


def _cited_goal(cited: list[dict[str, Any]], team: str) -> dict[str, Any]:
    goals = [e for e in cited if e["type"] == "shot" and e.get("outcome") == "goal" and e["team"] == team]
    if not goals:
        raise Unverifiable("no cited goal for this team")
    return goals[-1]


def _cited_shot(cited: list[dict[str, Any]], team: str) -> dict[str, Any]:
    shots = [e for e in cited if e["type"] == "shot" and e["team"] == team]
    if not shots:
        raise Unverifiable("no cited shot for this team")
    return shots[-1]


Recompute = Callable[[dict[str, Any], list[dict[str, Any]], dict[str, Any]], Any]


def _turnovers_won(moment, cited, doc):
    return sum(1 for e in cited if _is_turnover_won(e, moment["team"]))


def _turnovers_before_shot(moment, cited, doc):
    shot_t = _clock(_cited_shot(cited, moment["team"]))
    return sum(1 for e in cited if _is_turnover_won(e, moment["team"]) and _clock(e) <= shot_t)


def _high_turnovers(moment, cited, doc):
    opponent = _opponent(doc, moment["team"])
    return sum(
        1 for e in cited if _is_turnover_won(e, moment["team"]) and _in_defensive_half(doc, opponent, e)
    )


def _pressure_events(moment, cited, doc):
    return sum(1 for e in cited if e["type"] == "pressure" and e["team"] == moment["team"])


def _window_minutes(moment, cited, doc):
    if not cited:
        raise Unverifiable("no cited events")
    clocks = [_clock(e) for e in cited]
    return round((max(clocks) - min(clocks)) / 60, 1)


def _tackles_won(moment, cited, doc):
    player = moment["stats"].get("player") or (moment.get("entities") or {}).get("player")
    if not player:
        raise Unverifiable("milestone has no player")
    peak = parse_clock(moment["t_peak"])
    return sum(
        1
        for e in doc["events"]
        if e["type"] == "tackle"
        and e.get("outcome") == "won_possession"
        and e.get("player") == player
        and _clock(e) <= peak
    )


RECOMPUTE: dict[str, Recompute] = {
    "score_after": lambda m, c, d: _goals_until(d, parse_clock(m["t_peak"]), inclusive=True),
    "score_before": lambda m, c, d: _goals_until(d, parse_clock(m["t_peak"]), inclusive=False),
    "high_turnovers": _high_turnovers,
    "pressure_events": _pressure_events,
    "window_minutes": _window_minutes,
    "turnovers_before_shot": _turnovers_before_shot,
    "turnovers_won": _turnovers_won,
    "rk_turnovers_won": _turnovers_won,
    "shot_event_id": lambda m, c, d: _cited_shot(c, m["team"])["id"],
    "shot_outcome": lambda m, c, d: _cited_shot(c, m["team"]).get("outcome"),
    "scorer": lambda m, c, d: _cited_goal(c, m["team"]).get("player"),
    "minute": lambda m, c, d: _clock(_cited_goal(c, m["team"])) // 60,
    "tackles_won": _tackles_won,
}


def claims_for_moment(moment: dict[str, Any]) -> list[Claim]:
    stats = moment["stats"]
    claims = []
    for key, value in stats.items():
        if key in CONTEXT_KEYS:
            continue
        metric = stats["metric"] if key == "value" and "metric" in stats else key
        claims.append(Claim(moment["id"], metric, value, tuple(moment["event_ids"])))
    return claims


def stat_key_for(metric: str, moment: dict[str, Any]) -> str:
    """Map a claim metric back to the stat key it came from."""
    if moment["stats"].get("metric") == metric and "value" in moment["stats"]:
        return "value"
    return metric


class AgentsClaimChecker:
    """Prefer ``agents.verifier``; fall back for extra fact-layer metrics."""

    name = "agents-verifier-v1"

    def __init__(self) -> None:
        self._fallback = DeterministicClaimChecker()

    def check(self, claim: Claim, moment: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
        if claim.metric not in _AGENTS_METRICS:
            decision = self._fallback.check(claim, moment, doc)
            decision["checker"] = self.name
            decision["via"] = self._fallback.name
            return decision

        index = {e["id"]: e for e in doc["events"]}
        missing = [eid for eid in claim.event_ids if eid not in index]
        base: dict[str, Any] = {
            "moment_id": claim.moment_id,
            "metric": claim.metric,
            "claimed": claim.value,
            "event_ids": list(claim.event_ids),
            "recomputed": None,
            "status": "blocked",
            "reason": "",
            "checker": self.name,
            "via": "agents.verifier",
        }
        if missing:
            base["reason"] = f"cited events do not exist: {missing}"
            return base

        entities = dict(moment.get("entities") or {})
        stats = moment.get("stats") or {}
        if stats.get("shot_event_id"):
            entities.setdefault("shot_event_id", stats["shot_event_id"])
        if stats.get("player") or entities.get("player"):
            entities.setdefault("player", stats.get("player") or entities.get("player"))

        claim_dict = {
            "id": f"{claim.moment_id}:{claim.metric}",
            "match_id": doc["match"]["id"],
            "moment_id": claim.moment_id,
            "metric": claim.metric,
            "value": claim.value,
            "entities": entities,
            "event_ids": list(claim.event_ids),
            "sentence": f"{claim.metric}={claim.value!r}",
        }
        result = ClaimVerifier(doc).verify(claim_dict)
        base["recomputed"] = result.expected_value
        base["reason"] = result.reason
        base["event_ids_resolved"] = result.event_ids_resolved
        base["event_ids_missing"] = result.event_ids_missing

        if result.decision == "approved":
            base["status"] = "approved"
            base["reason"] = "matches raw events"
        elif result.decision == "corrected":
            # HTTP / UI contract: integer mismatches are blocked; float drift is corrected.
            expected = result.expected_value
            claimed = claim.value
            if (
                isinstance(expected, float)
                and isinstance(claimed, (int, float))
                and not isinstance(claimed, bool)
                and abs(float(expected) - float(claimed)) <= FLOAT_TOLERANCE
            ):
                base["status"] = "corrected"
                base["corrected_value"] = expected
                base["reason"] = f"rounding: raw events give {expected}"
            else:
                base["status"] = "blocked"
                base["reason"] = f"raw events give {expected!r}"
        else:
            base["status"] = "blocked"
            if result.event_ids_missing:
                base["reason"] = f"cited events do not exist: {result.event_ids_missing}"
        return base


class DeterministicClaimChecker:
    name = "deterministic-v1"

    def check(self, claim: Claim, moment: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "moment_id": claim.moment_id,
            "metric": claim.metric,
            "claimed": claim.value,
            "event_ids": list(claim.event_ids),
            "recomputed": None,
            "status": "blocked",
            "reason": "",
            "checker": self.name,
        }
        index = {e["id"]: e for e in doc["events"]}
        unknown = [eid for eid in claim.event_ids if eid not in index]
        if unknown:
            result["reason"] = f"cited events do not exist: {unknown}"
            return result
        cited = sorted((index[eid] for eid in claim.event_ids), key=lambda e: (_clock(e), e["id"]))

        rule = RECOMPUTE.get(claim.metric)
        if rule is None:
            result["reason"] = f"no recompute rule for metric {claim.metric!r}"
            return result
        try:
            actual = rule(moment, cited, doc)
        except Unverifiable as exc:
            result["reason"] = str(exc)
            return result

        result["recomputed"] = actual
        if actual == claim.value:
            result["status"] = "approved"
            result["reason"] = "matches raw events"
        elif (
            isinstance(actual, float)
            and isinstance(claim.value, (int, float))
            and not isinstance(claim.value, bool)
            and abs(actual - claim.value) <= FLOAT_TOLERANCE
        ):
            result["status"] = "corrected"
            result["corrected_value"] = actual
            result["reason"] = f"rounding: raw events give {actual}"
        else:
            result["reason"] = f"raw events give {actual!r}"
        return result


class AuditLog:
    """In-memory, process-local audit trail of verification decisions."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(self, match_id: str, decision: dict[str, Any], *, origin: str) -> dict[str, Any]:
        with self._lock:
            entry = {
                "seq": len(self._entries) + 1,
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "match_id": match_id,
                "origin": origin,
                **decision,
            }
            self._entries.append(entry)
            return entry

    def entries(self, match_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            return [e for e in self._entries if match_id is None or e["match_id"] == match_id]


def verify_moment(
    moment: dict[str, Any], doc: dict[str, Any], checker: ClaimChecker
) -> list[dict[str, Any]]:
    return [checker.check(claim, moment, doc) for claim in claims_for_moment(moment)]


def apply_verification(
    moment: dict[str, Any], decisions: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    """Return a copy of ``moment`` with corrected values applied and blocked stats removed,
    plus the stat keys that were blocked."""
    stats = dict(moment["stats"])
    blocked: list[str] = []
    for d in decisions:
        key = stat_key_for(d["metric"], moment)
        if d["status"] == "corrected":
            stats[key] = d["corrected_value"]
        elif d["status"] == "blocked":
            stats.pop(key, None)
            blocked.append(key)
    return {**moment, "stats": stats}, blocked

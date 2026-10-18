"""Deterministic claim verifier — approve / correct / block + audit log."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class VerificationResult:
    claim_id: str
    decision: str  # approved | corrected | blocked
    reason: str
    expected_value: Any = None
    corrected_claim: dict[str, Any] | None = None
    event_ids_resolved: list[str] = field(default_factory=list)
    event_ids_missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClaimVerifier:
    """Recompute claim metrics from raw match events."""

    def __init__(self, match_doc: dict[str, Any]) -> None:
        self.match_doc = match_doc
        self.match_id = match_doc["match"]["id"]
        self.home = match_doc["match"]["home"]["code"]
        self.away = match_doc["match"]["away"]["code"]
        self.events_by_id = {e["id"]: e for e in match_doc["events"]}
        self.audit_log: list[dict[str, Any]] = []
        self._audit_n = 0

    def verify(self, claim: dict[str, Any]) -> VerificationResult:
        claim_id = claim.get("id", "c-unknown")
        cited = list(claim.get("event_ids") or [])
        resolved = [eid for eid in cited if eid in self.events_by_id]
        missing = [eid for eid in cited if eid not in self.events_by_id]

        if missing:
            result = VerificationResult(
                claim_id=claim_id,
                decision="blocked",
                reason=f"missing_event_ids:{','.join(missing)}",
                event_ids_resolved=resolved,
                event_ids_missing=missing,
            )
            self._log(claim, result)
            return result

        metric = claim.get("metric")
        value = claim.get("value")
        entities = claim.get("entities") or {}
        events = [self.events_by_id[eid] for eid in resolved]

        try:
            expected = self._recompute(metric, value, entities, events, claim)
        except KeyError:
            result = VerificationResult(
                claim_id=claim_id,
                decision="blocked",
                reason=f"unknown_metric:{metric}",
                event_ids_resolved=resolved,
            )
            self._log(claim, result)
            return result
        except ValueError as exc:
            result = VerificationResult(
                claim_id=claim_id,
                decision="blocked",
                reason=str(exc),
                event_ids_resolved=resolved,
            )
            self._log(claim, result)
            return result

        if self._values_equal(value, expected):
            result = VerificationResult(
                claim_id=claim_id,
                decision="approved",
                reason="matches_events",
                expected_value=expected,
                event_ids_resolved=resolved,
            )
            self._log(claim, result)
            return result

        corrected = deepcopy(claim)
        corrected["value"] = expected
        corrected["sentence"] = self._rewrite_sentence(claim, expected)
        result = VerificationResult(
            claim_id=claim_id,
            decision="corrected",
            reason=f"value_mismatch:claimed={value!r}:expected={expected!r}",
            expected_value=expected,
            corrected_claim=corrected,
            event_ids_resolved=resolved,
        )
        self._log(claim, result)
        return result

    def verify_all(self, claims: list[dict[str, Any]]) -> list[VerificationResult]:
        return [self.verify(c) for c in claims]

    def inject_and_verify_wrong_stat(
        self,
        base_claim: dict[str, Any],
        *,
        wrong_value: Any,
    ) -> VerificationResult:
        """Demo helper: mutate a claim value and show it get corrected/blocked."""
        bad = deepcopy(base_claim)
        bad["id"] = f"{base_claim.get('id', 'c')}-injected"
        bad["value"] = wrong_value
        bad["sentence"] = (
            f"[INJECTED WRONG STAT] claimed {base_claim.get('metric')}={wrong_value}"
        )
        return self.verify(bad)

    def _recompute(
        self,
        metric: str | None,
        value: Any,
        entities: dict[str, Any],
        events: list[dict[str, Any]],
        claim: dict[str, Any],
    ) -> Any:
        if metric == "event_count":
            return len(events)
        if metric == "high_turnovers":
            return sum(1 for e in events if self._is_turnover_won(e))
        if metric == "pressure_events":
            return sum(1 for e in events if e.get("type") == "pressure")
        if metric == "turnovers_before_shot":
            return sum(
                1
                for e in events
                if self._is_turnover_won(e)
            )
        if metric == "shot_outcome":
            shot = self._find_shot(events, entities)
            if shot is None:
                raise ValueError("no_shot_event_for_shot_outcome")
            return shot.get("outcome")
        if metric == "goals":
            return sum(
                1
                for e in events
                if e.get("type") == "shot" and e.get("outcome") == "goal"
            )
        if metric == "tackles_won":
            player = entities.get("player")
            return sum(
                1
                for e in events
                if e.get("type") == "tackle"
                and e.get("outcome") == "won_possession"
                and (player is None or e.get("player") == player)
            )
        if metric == "score_after":
            # Prefer recomputing from all match goals up to max cited clock
            if events:
                max_t = max(self._clock(e["t"]) for e in events)
            else:
                max_t = 10**9
            home_g = away_g = 0
            for e in self.match_doc["events"]:
                if e.get("type") != "shot" or e.get("outcome") != "goal":
                    continue
                if self._clock(e["t"]) > max_t:
                    continue
                if e["team"] == self.home:
                    home_g += 1
                elif e["team"] == self.away:
                    away_g += 1
            return [home_g, away_g]
        if metric == "literal":
            attrs = claim.get("attrs") or {}
            if attrs.get("trusted"):
                return value
            raise ValueError("literal_not_trusted")
        raise KeyError(metric)

    @staticmethod
    def _is_turnover_won(event: dict[str, Any]) -> bool:
        return event.get("type") in {"tackle", "interception"} and event.get(
            "outcome"
        ) == "won_possession"

    @staticmethod
    def _find_shot(
        events: list[dict[str, Any]], entities: dict[str, Any]
    ) -> dict[str, Any] | None:
        shot_id = entities.get("shot_event_id")
        if shot_id:
            for e in events:
                if e["id"] == shot_id:
                    return e
        shots = [e for e in events if e.get("type") == "shot"]
        return shots[-1] if shots else None

    @staticmethod
    def _clock(t: str) -> int:
        m, s = t.split(":")
        return int(m) * 60 + int(s)

    @staticmethod
    def _values_equal(a: Any, b: Any) -> bool:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return float(a) == float(b)
        return a == b

    @staticmethod
    def _rewrite_sentence(claim: dict[str, Any], expected: Any) -> str:
        metric = claim.get("metric")
        return f"{metric} verified as {expected} (auto-corrected)"

    def _log(self, claim: dict[str, Any], result: VerificationResult) -> None:
        self._audit_n += 1
        self.audit_log.append(
            {
                "id": f"audit-{self._audit_n:04d}",
                "ts": datetime.now(timezone.utc).isoformat(),
                "match_id": claim.get("match_id") or self.match_id,
                "moment_id": claim.get("moment_id"),
                "claim_id": result.claim_id,
                "decision": result.decision,
                "reason": result.reason,
                "claim": deepcopy(claim),
                "expected_value": result.expected_value,
            }
        )

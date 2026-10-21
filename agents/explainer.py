"""Template explainer — emits schema v1 claims from moments.

Numbers stay here. ``agents.foundry.FoundryExplainer`` may rewrite sentences.
"""

from __future__ import annotations

from typing import Any


class TemplateExplainer:
    """Turn fact-layer moments into grounded claims.

    Foundry may rewrite claim sentences; metric/value/event_ids stay here.
    """

    def __init__(self, match_id: str) -> None:
        self.match_id = match_id
        self._n = 0

    def explain_moment(self, moment: dict[str, Any]) -> dict[str, Any]:
        claims = self._claims_for(moment)
        return {
            "schema_version": "1.0",
            "match_id": self.match_id,
            "moment_id": moment["id"],
            "summary_en": moment.get("headline", {}).get("en")
            or f"Moment {moment.get('type')}",
            "claims": claims,
        }

    def explain_all(self, moments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.explain_moment(m) for m in moments]

    def _next_id(self) -> str:
        self._n += 1
        return f"c-{self._n:04d}"

    def _base(self, moment: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        claim = {
            "id": self._next_id(),
            "match_id": self.match_id,
            "moment_id": moment["id"],
            "entities": dict(moment.get("entities") or {}),
            "event_ids": list(moment.get("event_ids") or []),
        }
        claim.update(kwargs)
        return claim

    def _claims_for(self, moment: dict[str, Any]) -> list[dict[str, Any]]:
        mtype = moment.get("type")
        stats = moment.get("stats") or {}
        team = moment.get("team")
        handlers = {
            "pressure_spell": self._pressure,
            "shot_after_turnovers": self._shot_after_turnovers,
            "momentum_swing": self._momentum,
            "goal": self._goal,
            "player_milestone": self._milestone,
        }
        fn = handlers.get(mtype)
        if fn is None:
            return [
                self._base(
                    moment,
                    sentence=moment.get("headline", {}).get("en") or mtype,
                    metric="event_count",
                    value=len(moment.get("event_ids") or []),
                    entities={"team": team},
                )
            ]
        return fn(moment, stats, team)

    def _pressure(
        self, moment: dict[str, Any], stats: dict[str, Any], team: str | None
    ) -> list[dict[str, Any]]:
        turns = int(stats.get("high_turnovers") or 0)
        press = int(stats.get("pressure_events") or 0)
        return [
            self._base(
                moment,
                sentence=(
                    f"{team} forced {turns} high turnovers during the press window."
                ),
                metric="high_turnovers",
                value=turns,
                entities={"team": team, "opponent": (moment.get("entities") or {}).get("opponent")},
            ),
            self._base(
                moment,
                sentence=f"{team} recorded {press} pressure events in the spell.",
                metric="pressure_events",
                value=press,
                entities={"team": team},
            ),
        ]

    def _shot_after_turnovers(
        self, moment: dict[str, Any], stats: dict[str, Any], team: str | None
    ) -> list[dict[str, Any]]:
        n = int(stats.get("turnovers_before_shot") or 0)
        outcome = stats.get("shot_outcome")
        shot_id = stats.get("shot_event_id")
        entities = {"team": team, "shooter": (moment.get("entities") or {}).get("shooter")}
        if shot_id:
            entities["shot_event_id"] = shot_id
        claims = [
            self._base(
                moment,
                sentence=f"{team} won {n} turnovers before creating the shot.",
                metric="turnovers_before_shot",
                value=n,
                entities=entities,
            )
        ]
        if outcome is not None:
            claims.append(
                self._base(
                    moment,
                    sentence=f"The resulting shot outcome was {outcome}.",
                    metric="shot_outcome",
                    value=outcome,
                    entities=entities,
                )
            )
        return claims

    def _momentum(
        self, moment: dict[str, Any], stats: dict[str, Any], team: str | None
    ) -> list[dict[str, Any]]:
        score_after = stats.get("score_after") or [0, 0]
        turns = int(stats.get("turnovers_won") or stats.get("rk_turnovers_won") or 0)
        return [
            self._base(
                moment,
                sentence=f"Scoreline after the swing: {score_after[0]}-{score_after[1]}.",
                metric="score_after",
                value=list(score_after),
                entities={"team": team},
            ),
            self._base(
                moment,
                sentence=f"{team} had won {turns} turnovers in the build-up window.",
                metric="high_turnovers",
                value=turns,
                entities={"team": team},
            ),
        ]

    def _goal(
        self, moment: dict[str, Any], stats: dict[str, Any], team: str | None
    ) -> list[dict[str, Any]]:
        score_after = stats.get("score_after") or [0, 0]
        scorer = stats.get("scorer") or (moment.get("entities") or {}).get("scorer")
        return [
            self._base(
                moment,
                sentence=f"{team} scored; score afterwards {score_after[0]}-{score_after[1]}.",
                metric="goals",
                value=1,
                entities={"team": team, "scorer": scorer},
            ),
            self._base(
                moment,
                sentence=f"Match score after the goal: {score_after[0]}-{score_after[1]}.",
                metric="score_after",
                value=list(score_after),
                entities={"team": team, "scorer": scorer},
            ),
        ]

    def _milestone(
        self, moment: dict[str, Any], stats: dict[str, Any], team: str | None
    ) -> list[dict[str, Any]]:
        player = stats.get("player") or (moment.get("entities") or {}).get("player")
        value = int(stats.get("value") or 0)
        # Milestone fixtures may cite all of a player's tackles; value is match tally.
        return [
            self._base(
                moment,
                sentence=f"{player} reached {value} tackles won.",
                metric="tackles_won",
                value=value,
                entities={"team": team, "player": player},
            )
        ]

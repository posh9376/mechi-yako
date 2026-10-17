"""Incremental match-state aggregator (deterministic — no LLM)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from pipeline.clock import format_clock, parse_clock

# Events that count toward a crude possession / activity share
_ACTIVITY_TYPES = frozenset(
    {"pass", "carry", "shot", "tackle", "interception", "pressure", "clearance", "block"}
)
_TURNOVER_WON = frozenset({"tackle", "interception"})


@dataclass
class TeamStats:
    passes_attempted: int = 0
    passes_complete: int = 0
    shots: int = 0
    shots_on_target: int = 0
    goals: int = 0
    tackles_won: int = 0
    interceptions: int = 0
    pressure_events: int = 0
    activity: int = 0

    @property
    def pass_completion(self) -> float | None:
        if self.passes_attempted == 0:
            return None
        return self.passes_complete / self.passes_attempted


@dataclass
class MatchState:
    """Snapshot of aggregate state after N events."""

    match_id: str
    home: str
    away: str
    clock: str = "0:00"
    period: int = 1
    score: list[int] = field(default_factory=lambda: [0, 0])
    events_seen: int = 0
    teams: dict[str, TeamStats] = field(default_factory=dict)
    # Rolling windows: list of (clock_s, team, kind, event_id, location)
    recent: list[tuple[int, str, str, str, list[float] | None]] = field(
        default_factory=list, repr=False
    )
    player_tackles_won: dict[str, int] = field(default_factory=dict)
    last_event_id: str | None = None

    def possession_share(self) -> dict[str, float]:
        total = sum(t.activity for t in self.teams.values()) or 1
        return {code: stats.activity / total for code, stats in self.teams.items()}

    def to_dict(self) -> dict[str, Any]:
        shares = self.possession_share()
        return {
            "match_id": self.match_id,
            "clock": self.clock,
            "period": self.period,
            "score": list(self.score),
            "events_seen": self.events_seen,
            "possession": {k: round(v, 3) for k, v in shares.items()},
            "teams": {
                code: {
                    "passes_attempted": s.passes_attempted,
                    "passes_complete": s.passes_complete,
                    "pass_completion": None
                    if s.pass_completion is None
                    else round(s.pass_completion, 3),
                    "shots": s.shots,
                    "shots_on_target": s.shots_on_target,
                    "goals": s.goals,
                    "tackles_won": s.tackles_won,
                    "interceptions": s.interceptions,
                    "pressure_events": s.pressure_events,
                }
                for code, s in self.teams.items()
            },
            "player_tackles_won": dict(self.player_tackles_won),
            "last_event_id": self.last_event_id,
        }


class MatchStateAggregator:
    """Fold events into match state. Safe to call once per replayed event."""

    def __init__(self, match_meta: dict[str, Any], *, window_seconds: int = 600) -> None:
        home = match_meta["home"]["code"]
        away = match_meta["away"]["code"]
        self.window_seconds = window_seconds
        self.state = MatchState(
            match_id=match_meta["id"],
            home=home,
            away=away,
            teams={home: TeamStats(), away: TeamStats()},
        )

    def ingest(self, event: dict[str, Any]) -> MatchState:
        st = self.state
        team = event["team"]
        if team not in st.teams:
            st.teams[team] = TeamStats()
        stats = st.teams[team]
        etype = event["type"]
        outcome = event.get("outcome")
        loc = event.get("location")
        eid = event["id"]
        clock_s = parse_clock(event["t"])

        st.clock = event["t"]
        st.period = int(event.get("period") or st.period)
        st.events_seen += 1
        st.last_event_id = eid

        if etype in _ACTIVITY_TYPES:
            stats.activity += 1

        if etype == "pass":
            stats.passes_attempted += 1
            if outcome == "complete":
                stats.passes_complete += 1
        elif etype == "shot":
            stats.shots += 1
            if outcome in {"goal", "saved", "woodwork"}:
                stats.shots_on_target += 1
            if outcome == "goal":
                stats.goals += 1
                if team == st.home:
                    st.score[0] += 1
                elif team == st.away:
                    st.score[1] += 1
        elif etype == "tackle" and outcome == "won_possession":
            stats.tackles_won += 1
            player = event.get("player")
            if player:
                st.player_tackles_won[player] = st.player_tackles_won.get(player, 0) + 1
        elif etype == "interception" and outcome == "won_possession":
            stats.interceptions += 1
        elif etype == "pressure":
            stats.pressure_events += 1

        kind = etype
        if etype in _TURNOVER_WON and outcome == "won_possession":
            kind = "turnover_won"
        st.recent.append((clock_s, team, kind, eid, loc if isinstance(loc, list) else None))
        self._trim_window(clock_s)
        return st

    def _trim_window(self, now_s: int) -> None:
        cutoff = now_s - self.window_seconds
        recent = self.state.recent
        i = 0
        while i < len(recent) and recent[i][0] < cutoff:
            i += 1
        if i:
            del recent[:i]

    def ingest_all(self, events: list[dict[str, Any]]) -> MatchState:
        for event in events:
            self.ingest(event)
        return self.state

    def snapshot(self) -> dict[str, Any]:
        return self.state.to_dict()

    def window_events(
        self,
        *,
        team: str | None = None,
        kinds: set[str] | None = None,
        in_half: str | None = None,
    ) -> list[tuple[int, str, str, str, list[float] | None]]:
        """Filter the rolling window.

        in_half: ``\"home\"`` means x < 50 (home defensive half in schema v1),
        ``\"away\"`` means x >= 50.
        """
        out = []
        for item in self.state.recent:
            clock_s, tcode, kind, eid, loc = item
            if team is not None and tcode != team:
                continue
            if kinds is not None and kind not in kinds:
                continue
            if in_half is not None and loc is not None:
                x = loc[0]
                if in_half == "home" and not (x < 50):
                    continue
                if in_half == "away" and not (x >= 50):
                    continue
            out.append(item)
        return out

    def copy_state(self) -> MatchState:
        return deepcopy(self.state)

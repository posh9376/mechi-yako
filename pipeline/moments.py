"""Deterministic moment detector (no LLM). Emits fact-layer-shaped moments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.clock import format_clock, parse_clock
from pipeline.state import MatchStateAggregator


@dataclass
class DetectorConfig:
    pressure_min_events: int = 3
    pressure_min_turnovers: int = 3
    pressure_window_s: int = 420  # 7 minutes
    turnovers_before_shot: int = 3
    shot_lookback_s: int = 360
    milestone_tackles: int = 5


class MomentDetector:
    """Scan a match (optionally online) and emit ranked moments."""

    def __init__(
        self,
        match_meta: dict[str, Any],
        *,
        config: DetectorConfig | None = None,
    ) -> None:
        self.match_meta = match_meta
        self.match_id = match_meta["id"]
        self.home = match_meta["home"]["code"]
        self.away = match_meta["away"]["code"]
        self.config = config or DetectorConfig()
        self.agg = MatchStateAggregator(
            match_meta, window_seconds=max(600, self.config.pressure_window_s)
        )
        self._moments: list[dict[str, Any]] = []
        self._emitted_keys: set[str] = set()
        self._seq = 0
        self._pressure_open: dict[str, dict[str, Any]] | None = None

    @property
    def moments(self) -> list[dict[str, Any]]:
        return list(self._moments)

    def ingest(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Ingest one event; return any newly detected moments."""
        before_score = list(self.agg.state.score)
        self.agg.ingest(event)
        new: list[dict[str, Any]] = []

        new.extend(self._check_pressure(event))
        new.extend(self._check_shot_after_turnovers(event))
        new.extend(self._check_goal(event, before_score))
        new.extend(self._check_milestone(event))

        for m in new:
            self._moments.append(m)
        return new

    def detect_all(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._moments.clear()
        self._emitted_keys.clear()
        self._seq = 0
        self.agg = MatchStateAggregator(
            self.match_meta, window_seconds=max(600, self.config.pressure_window_s)
        )
        for event in sorted(events, key=lambda e: (parse_clock(e["t"]), e["id"])):
            self.ingest(event)
        # Close any open pressure spell at end of window activity
        self._finalize_pressure()
        return self.moments

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"mom-{prefix}-{self._seq:02d}"

    def _player_name(self, player_id: str | None) -> str | None:
        if not player_id:
            return None
        for side in ("home", "away"):
            for p in self.match_meta[side]["players"]:
                if p["id"] == player_id:
                    return p["name"]
        return player_id

    def _check_pressure(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Track a running pressure spell; emit when spell ends or on goal."""
        cfg = self.config
        now = parse_clock(event["t"])
        out: list[dict[str, Any]] = []

        for team in (self.home, self.away):
            opponent = self.away if team == self.home else self.home
            # High turnovers = won in opponent's defensive half relative to opponent.
            # Schema: home defends x<50. So turnovers in BH half are loc x<50.
            half = "home" if opponent == self.home else "away"
            press = self.agg.window_events(
                team=team, kinds={"pressure"}, in_half=half
            )
            turns = self.agg.window_events(
                team=team, kinds={"turnover_won"}, in_half=half
            )
            # Also count turnovers without strict half filter if location missing
            if not turns:
                turns = self.agg.window_events(team=team, kinds={"turnover_won"})

            # Narrow to last pressure_window_s
            press = [x for x in press if now - x[0] <= cfg.pressure_window_s]
            turns = [x for x in turns if now - x[0] <= cfg.pressure_window_s]

            active = (
                len(press) >= cfg.pressure_min_events
                and len(turns) >= cfg.pressure_min_turnovers
            )
            key = f"pressure:{team}"

            if active:
                if key not in self._emitted_keys:
                    # Mark open; emit once when we leave the spell or at peak density
                    if self._pressure_open is None:
                        self._pressure_open = {}
                    self._pressure_open[team] = {
                        "press": press,
                        "turns": turns,
                        "peak_event": event,
                    }
            else:
                if self._pressure_open and team in self._pressure_open:
                    mom = self._emit_pressure(team, self._pressure_open.pop(team))
                    if mom:
                        out.append(mom)
                        self._emitted_keys.add(key)

        return out

    def _finalize_pressure(self) -> None:
        if not self._pressure_open:
            return
        for team, payload in list(self._pressure_open.items()):
            key = f"pressure:{team}"
            if key in self._emitted_keys:
                continue
            mom = self._emit_pressure(team, payload)
            if mom:
                self._moments.append(mom)
                self._emitted_keys.add(key)
        self._pressure_open = {}

    def _emit_pressure(self, team: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        press: list = payload["press"]
        turns: list = payload["turns"]
        if not press and not turns:
            return None
        all_items = sorted(press + turns, key=lambda x: x[0])
        t_start = format_clock(all_items[0][0])
        t_end = format_clock(all_items[-1][0])
        # Peak at densest turnover
        peak = turns[-1] if turns else all_items[-1]
        opponent = self.away if team == self.home else self.home
        event_ids = list(dict.fromkeys([x[3] for x in press + turns]))
        key_player = None
        best = 0
        for pid, n in self.agg.state.player_tackles_won.items():
            if pid.startswith(team) and n > best:
                best = n
                key_player = pid

        return {
            "id": self._next_id("pressure"),
            "match_id": self.match_id,
            "type": "pressure_spell",
            "t_start": t_start,
            "t_end": t_end,
            "t_peak": format_clock(peak[0]),
            "team": team,
            "headline": {
                "en": (
                    f"{self._team_name(team)} pressed high and forced repeated "
                    f"turnovers in the {self._team_name(opponent)} half."
                )
            },
            "significance": min(0.95, 0.7 + 0.03 * len(turns) + 0.02 * len(press)),
            "event_ids": event_ids,
            "stats": {
                "high_turnovers": len(turns),
                "pressure_events": len(press),
                "window_minutes": round((all_items[-1][0] - all_items[0][0]) / 60, 1),
                "zone": f"{opponent}_own_half",
            },
            "entities": {
                "team": team,
                "opponent": opponent,
                "key_player": key_player,
            },
        }

    def _check_shot_after_turnovers(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        if event["type"] != "shot":
            return []
        team = event["team"]
        key = f"shot_to:{event['id']}"
        if key in self._emitted_keys:
            return []
        now = parse_clock(event["t"])
        turns = [
            x
            for x in self.agg.window_events(team=team, kinds={"turnover_won"})
            if now - x[0] <= self.config.shot_lookback_s and x[0] <= now
        ]
        if len(turns) < self.config.turnovers_before_shot:
            return []
        self._emitted_keys.add(key)
        t_start = format_clock(turns[0][0])
        return [
            {
                "id": self._next_id("shot-to"),
                "match_id": self.match_id,
                "type": "shot_after_turnovers",
                "t_start": t_start,
                "t_end": event["t"],
                "t_peak": event["t"],
                "team": team,
                "headline": {
                    "en": (
                        f"After several won tackles, {self._team_name(team)} created a shot."
                    )
                },
                "significance": 0.78,
                "event_ids": [x[3] for x in turns[-4:]] + [event["id"]],
                "stats": {
                    "turnovers_before_shot": len(turns),
                    "shot_event_id": event["id"],
                    "shot_outcome": event.get("outcome"),
                },
                "entities": {"team": team, "shooter": event.get("player")},
            }
        ]

    def _check_goal(
        self, event: dict[str, Any], score_before: list[int]
    ) -> list[dict[str, Any]]:
        if event["type"] != "shot" or event.get("outcome") != "goal":
            return []
        team = event["team"]
        key = f"goal:{event['id']}"
        if key in self._emitted_keys:
            return []
        self._emitted_keys.add(key)
        score_after = list(self.agg.state.score)
        scorer = event.get("player")
        name = self._player_name(scorer) or scorer or self._team_name(team)
        minute = parse_clock(event["t"]) // 60
        out = [
            {
                "id": self._next_id("goal"),
                "match_id": self.match_id,
                "type": "goal",
                "t_start": event["t"],
                "t_end": event["t"],
                "t_peak": event["t"],
                "team": team,
                "headline": {
                "en": (
                    f"{name} scored for {self._team_name(team)} "
                    f"in the {self._ordinal(minute)} minute."
                )
            },
                "significance": 0.95,
                "event_ids": [event["id"]],
                "stats": {
                    "score_after": score_after,
                    "scorer": scorer,
                    "minute": minute,
                },
                "entities": {"scorer": scorer, "team": team},
            }
        ]

        # Momentum swing: equaliser or lead change after trailing / following press
        became_level = score_after[0] == score_after[1]
        press_key = f"pressure:{team}"
        # If pressure was open or already emitted for this team recently, attach swing
        recent_press = any(
            m["type"] == "pressure_spell" and m["team"] == team for m in self._moments
        ) or (self._pressure_open and team in (self._pressure_open or {}))
        if became_level or recent_press:
            swing_key = f"momentum:{event['id']}"
            if swing_key not in self._emitted_keys:
                self._emitted_keys.add(swing_key)
                turns = self.agg.window_events(team=team, kinds={"turnover_won"})
                out.append(
                    {
                        "id": self._next_id("momentum"),
                        "match_id": self.match_id,
                        "type": "momentum_swing",
                        "t_start": format_clock(turns[0][0]) if turns else event["t"],
                        "t_end": event["t"],
                        "t_peak": event["t"],
                        "team": team,
                        "headline": {
                            "en": (
                                f"The press flipped the half: {self._team_name(team)} "
                                f"changed the scoreline."
                            )
                        },
                        "significance": 0.9,
                        "event_ids": [x[3] for x in turns] + [event["id"]],
                        "stats": {
                            "score_before": score_before,
                            "score_after": score_after,
                            "rk_turnovers_won": len(turns)
                            if team == self.away
                            else len(turns),
                            "turnovers_won": len(turns),
                        },
                        "entities": {
                            "team": team,
                            "opponent": self.away if team == self.home else self.home,
                        },
                    }
                )
            # Also flush pressure spell tied to this goal
            if self._pressure_open and team in self._pressure_open:
                mom = self._emit_pressure(team, self._pressure_open.pop(team))
                if mom and f"pressure:{team}" not in self._emitted_keys:
                    self._emitted_keys.add(f"pressure:{team}")
                    out.insert(0, mom)
        return out

    def _check_milestone(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        if event["type"] != "tackle" or event.get("outcome") != "won_possession":
            return []
        player = event.get("player")
        if not player:
            return []
        count = self.agg.state.player_tackles_won.get(player, 0)
        if count < self.config.milestone_tackles:
            return []
        key = f"milestone:{player}:{self.config.milestone_tackles}"
        if key in self._emitted_keys:
            return []
        self._emitted_keys.add(key)
        # Collect this player's won tackles from full recent + attrs
        # Use all events seen via a light scan of aggregator's... we only have counts.
        # Attach last N tackle event ids from recent window where we can; else just this event.
        team = event["team"]
        name = self._player_name(player) or player
        return [
            {
                "id": self._next_id("milestone"),
                "match_id": self.match_id,
                "type": "player_milestone",
                "t_start": event["t"],
                "t_end": event["t"],
                "t_peak": event["t"],
                "team": team,
                "headline": {
                    "en": (
                        f"{name} won a {self._ordinal(count)} tackle, "
                        f"capping a strong defensive shift."
                    )
                },
                "significance": 0.72,
                "event_ids": [event["id"]],
                "stats": {
                    "player": player,
                    "metric": "tackles_won",
                    "value": count,
                    "milestone": f"{count}th_tackle_won",
                },
                "entities": {"player": player, "team": team},
            }
        ]

    def _team_name(self, code: str) -> str:
        if code == self.home:
            return self.match_meta["home"]["name"]
        if code == self.away:
            return self.match_meta["away"]["name"]
        return code

    @staticmethod
    def _ordinal(n: int) -> str:
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

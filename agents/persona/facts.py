"""Language-neutral facts pulled from one moment. Writers may only print what is here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.clock import parse_clock


class UnsupportedMoment(ValueError):
    pass


@dataclass(frozen=True)
class MomentFacts:
    moment: dict[str, Any]
    match_meta: dict[str, Any]
    team: str
    team_name: str
    opponent: str
    opponent_name: str
    home_name: str
    away_name: str
    minute_start: int
    minute_end: int
    minute_peak: int
    home_code: str

    @property
    def type(self) -> str:
        return self.moment["type"]

    @property
    def stats(self) -> dict[str, Any]:
        return self.moment["stats"]

    @property
    def entities(self) -> dict[str, Any]:
        return self.moment.get("entities") or {}

    def turnovers_key(self) -> str:
        for key in ("turnovers_won", "rk_turnovers_won"):
            if key in self.stats:
                return key
        raise UnsupportedMoment(f"{self.moment['id']} has no turnover count")

    def goal_situation(self) -> str:
        """``level`` / ``ahead`` / ``behind`` for the scoring team after a goal."""
        home_goals, away_goals = self.stats["score_after"]
        if home_goals == away_goals:
            return "level"
        team_is_home = self.team == self.home_code
        mine, theirs = (home_goals, away_goals) if team_is_home else (away_goals, home_goals)
        return "ahead" if mine > theirs else "behind"


def _minute(clock: str) -> int:
    return parse_clock(clock) // 60


def _team_name(meta: dict[str, Any], code: str) -> str:
    for side in ("home", "away"):
        if meta[side]["code"] == code:
            return meta[side]["name"]
    return code


def player_name(meta: dict[str, Any], player_id: str | None) -> str:
    if not player_id:
        raise UnsupportedMoment("moment is missing a player id")
    for side in ("home", "away"):
        for p in meta[side]["players"]:
            if p["id"] == player_id:
                return p["name"]
    raise UnsupportedMoment(f"unknown player {player_id!r}")


def build_facts(moment: dict[str, Any], match_meta: dict[str, Any]) -> MomentFacts:
    home, away = match_meta["home"]["code"], match_meta["away"]["code"]
    team = moment["team"]
    opponent = away if team == home else home
    return MomentFacts(
        moment=moment,
        match_meta=match_meta,
        team=team,
        team_name=_team_name(match_meta, team),
        opponent=opponent,
        opponent_name=_team_name(match_meta, opponent),
        home_name=match_meta["home"]["name"],
        away_name=match_meta["away"]["name"],
        minute_start=_minute(moment["t_start"]),
        minute_end=_minute(moment["t_end"]),
        minute_peak=_minute(moment["t_peak"]),
        home_code=home,
    )

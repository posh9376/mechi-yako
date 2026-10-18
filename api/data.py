"""Load match documents, fact-layer fixtures and live-detected moments."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pipeline.moments import MomentDetector
from pipeline.replay import load_match

ROOT = Path(__file__).resolve().parents[1]
MATCHES_DIR = ROOT / "data" / "matches"
FIXTURES_DIR = ROOT / "data" / "fixtures"

MomentSource = Literal["fixture", "live"]

_MATCH_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class MatchNotFound(LookupError):
    pass


class MomentNotFound(LookupError):
    pass


def _match_path(match_id: str) -> Path:
    if not _MATCH_ID.match(match_id):
        raise MatchNotFound(match_id)
    path = MATCHES_DIR / f"{match_id}.json"
    if not path.is_file():
        raise MatchNotFound(match_id)
    return path


def available_matches() -> list[str]:
    return sorted(p.stem for p in MATCHES_DIR.glob("*.json"))


@lru_cache(maxsize=16)
def get_match_doc(match_id: str) -> dict[str, Any]:
    return load_match(_match_path(match_id))


@lru_cache(maxsize=16)
def get_fixture(match_id: str) -> dict[str, Any]:
    _match_path(match_id)
    path = FIXTURES_DIR / f"{match_id}.moments.json"
    if not path.is_file():
        raise MatchNotFound(match_id)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=16)
def get_live_moments(match_id: str) -> tuple[dict[str, Any], ...]:
    doc = get_match_doc(match_id)
    moments = MomentDetector(doc["match"]).detect_all(doc["events"])
    return tuple(moments)


def get_moments(match_id: str, source: MomentSource) -> list[dict[str, Any]]:
    if source == "fixture":
        return list(get_fixture(match_id)["moments"])
    return list(get_live_moments(match_id))


def get_moment(match_id: str, moment_id: str, source: MomentSource) -> dict[str, Any]:
    for moment in get_moments(match_id, source):
        if moment["id"] == moment_id:
            return moment
    raise MomentNotFound(moment_id)


def player_name(match_meta: dict[str, Any], player_id: str | None) -> str | None:
    if not player_id:
        return None
    for side in ("home", "away"):
        for p in match_meta[side]["players"]:
            if p["id"] == player_id:
                return p["name"]
    return None


def team_name(match_meta: dict[str, Any], code: str) -> str:
    for side in ("home", "away"):
        if match_meta[side]["code"] == code:
            return match_meta[side]["name"]
    return code


def opponent_code(match_meta: dict[str, Any], code: str) -> str:
    home, away = match_meta["home"]["code"], match_meta["away"]["code"]
    return away if code == home else home

"""Hand-scripted demo match: Blue Herons vs Red Kites (m-demo-001).

Storyline (locked):
- BH lead 1-0 at HT
- RK press from ~55', turnovers in BH half
- RK equalise ~63'
- RK player milestone late
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

MATCH_ID = "m-demo-001"
SCHEMA_VERSION = "1.0"


def _teams() -> tuple[dict[str, Any], dict[str, Any]]:
    home = {
        "code": "BH",
        "name": "Blue Herons",
        "players": [
            {"id": "BH-1", "name": "Kofi Mensah", "number": 1, "position": "GK"},
            {"id": "BH-2", "name": "Sam Okello", "number": 2, "position": "DEF"},
            {"id": "BH-4", "name": "Imani Wekesa", "number": 4, "position": "DEF"},
            {"id": "BH-5", "name": "Noah Baraka", "number": 5, "position": "DEF"},
            {"id": "BH-6", "name": "Lila Njoroge", "number": 6, "position": "MID"},
            {"id": "BH-8", "name": "Ethan Otieno", "number": 8, "position": "MID"},
            {"id": "BH-10", "name": "Asha Kamau", "number": 10, "position": "MID"},
            {"id": "BH-7", "name": "Milo Cheruiyot", "number": 7, "position": "FWD"},
            {"id": "BH-9", "name": "Zuri Mwangi", "number": 9, "position": "FWD"},
            {"id": "BH-11", "name": "Tariq Hassan", "number": 11, "position": "FWD"},
            {"id": "BH-3", "name": "Pia Mutiso", "number": 3, "position": "DEF"},
        ],
    }
    away = {
        "code": "RK",
        "name": "Red Kites",
        "players": [
            {"id": "RK-1", "name": "Juma Ochieng", "number": 1, "position": "GK"},
            {"id": "RK-2", "name": "Elena Kruk", "number": 2, "position": "DEF"},
            {"id": "RK-3", "name": "Diego Santos", "number": 3, "position": "DEF"},
            {"id": "RK-4", "name": "Makena Aoko", "number": 4, "position": "DEF"},
            {"id": "RK-5", "name": "Farid Yusuf", "number": 5, "position": "MID"},
            {"id": "RK-6", "name": "Sanaa Rehema", "number": 6, "position": "MID"},
            {"id": "RK-8", "name": "Leo Ndungu", "number": 8, "position": "MID"},
            {"id": "RK-7", "name": "Nina Wambui", "number": 7, "position": "FWD"},
            {"id": "RK-9", "name": "Omar Diallo", "number": 9, "position": "FWD"},
            {"id": "RK-10", "name": "Vera Kimani", "number": 10, "position": "FWD"},
            {"id": "RK-11", "name": "Chris Otieno", "number": 11, "position": "FWD"},
        ],
    }
    return home, away


class _Builder:
    def __init__(self, match_id: str = MATCH_ID) -> None:
        self.match_id = match_id
        self._n = 0
        self.events: list[dict[str, Any]] = []

    def add(
        self,
        t: str,
        period: int,
        type_: str,
        team: str,
        player: str | None,
        location: list[float] | None,
        outcome: str | None,
        *,
        related: list[str] | None = None,
        attrs: dict[str, Any] | None = None,
    ) -> str:
        self._n += 1
        eid = f"e-{self._n:04d}"
        ev: dict[str, Any] = {
            "id": eid,
            "t": t,
            "period": period,
            "type": type_,
            "team": team,
            "player": player,
            "location": location,
            "outcome": outcome,
            "match_id": self.match_id,
        }
        if related:
            ev["related_event_ids"] = related
        if attrs:
            ev["attrs"] = attrs
        self.events.append(ev)
        return eid


def _pass_chain(b: _Builder, t0_min: int, t0_sec: int, period: int, team: str, players: list[str], xs: list[float], complete: bool = True) -> list[str]:
    """Emit a short sequence of passes; last may be incomplete."""
    ids: list[str] = []
    sec = t0_min * 60 + t0_sec
    for i, player in enumerate(players[:-1]):
        m, s = divmod(sec + i * 3, 60)
        loc = [xs[i], 40.0 + (i % 3) * 5]
        outcome = "complete" if (complete or i < len(players) - 2) else "incomplete"
        if not complete and i == len(players) - 2:
            outcome = "incomplete"
        ids.append(
            b.add(f"{m}:{s:02d}", period, "pass", team, player, loc, outcome)
        )
    return ids


def build_demo_match() -> dict[str, Any]:
    home, away = _teams()
    b = _Builder()

    # --- First half: BH mostly in control, score 1-0 ---
    b.add("0:00", 1, "kickoff", "BH", "BH-9", [50.0, 50.0], "started")

    # Calm BH build-up (mix of complete and broken chains)
    for minute in (2, 5, 8, 11, 14, 17):
        _pass_chain(
            b,
            minute,
            10,
            1,
            "BH",
            ["BH-4", "BH-6", "BH-8", "BH-10"],
            [25.0, 35.0, 48.0, 60.0],
            complete=(minute % 4 != 1),
        )

    # RK probes — several incomplete
    for minute in (3, 6, 9, 12, 16, 18):
        _pass_chain(
            b,
            minute,
            20,
            1,
            "RK",
            ["RK-5", "RK-8", "RK-10"],
            [55.0, 62.0, 70.0],
            complete=(minute in (9, 18)),
        )

    # BH goal ~20'
    pre = b.add("19:42", 1, "pass", "BH", "BH-10", [72.0, 48.0], "complete")
    shot = b.add(
        "19:55",
        1,
        "shot",
        "BH",
        "BH-9",
        [88.0, 52.0],
        "goal",
        related=[pre],
        attrs={"xg": 0.42, "body_part": "right_foot"},
    )
    b.add("19:56", 1, "save", "RK", "RK-1", [99.0, 50.0], "conceded", related=[shot])

    # More first-half traffic
    for minute in (22, 24, 26, 30, 32, 34, 38, 40, 42):
        team = "BH" if minute % 2 == 0 else "RK"
        plist = (
            ["BH-5", "BH-6", "BH-8", "BH-7"]
            if team == "BH"
            else ["RK-4", "RK-5", "RK-6", "RK-9"]
        )
        xs = [30.0, 45.0, 58.0, 70.0] if team == "BH" else [70.0, 55.0, 42.0, 30.0]
        _pass_chain(b, minute, 5, 1, team, plist, xs, complete=(minute not in (24, 32, 40)))
        if team == "RK":
            b.add(f"{minute}:40", 1, "pressure", "BH", "BH-6", [60.0, 50.0], "applied")

    # A few shots
    b.add("28:12", 1, "shot", "BH", "BH-7", [81.0, 40.0], "saved")
    b.add("28:13", 1, "save", "RK", "RK-1", [98.0, 44.0], "held")
    b.add("36:40", 1, "shot", "RK", "RK-9", [18.0, 55.0], "off_target")

    b.add("45:00", 1, "period_end", "BH", None, None, "ended")

    # --- Second half ---
    b.add("45:00", 2, "kickoff", "RK", "RK-9", [50.0, 50.0], "started")

    for minute in (46, 47, 49, 50, 52, 53):
        _pass_chain(
            b,
            minute,
            0,
            2,
            "BH" if minute < 52 else "RK",
            ["BH-4", "BH-5", "BH-6", "BH-8"]
            if minute < 52
            else ["RK-5", "RK-6", "RK-8", "RK-10"],
            [40.0, 48.0, 55.0, 62.0] if minute < 52 else [58.0, 50.0, 42.0, 35.0],
            complete=(minute not in (47, 53)),
        )

    # Pressure spell ~55'–62': RK force turnovers in BH half (x < 50 for BH)
    pressure_ids: list[str] = []
    turnover_ids: list[str] = []

    pressure_ids.append(
        b.add("55:05", 2, "pressure", "RK", "RK-8", [42.0, 48.0], "applied")
    )
    t1 = b.add("55:18", 2, "tackle", "RK", "RK-4", [38.0, 44.0], "won_possession")
    turnover_ids.append(t1)
    pressure_ids.append(t1)

    pressure_ids.append(
        b.add("56:02", 2, "pressure", "RK", "RK-6", [35.0, 60.0], "applied")
    )
    t2 = b.add("56:10", 2, "interception", "RK", "RK-5", [33.0, 55.0], "won_possession")
    turnover_ids.append(t2)

    # BH try to play out, lose it again
    b.add("57:20", 2, "pass", "BH", "BH-4", [28.0, 40.0], "incomplete")
    t3 = b.add("57:22", 2, "tackle", "RK", "RK-4", [30.0, 42.0], "won_possession")
    turnover_ids.append(t3)
    pressure_ids.append(
        b.add("57:40", 2, "pressure", "RK", "RK-10", [40.0, 50.0], "applied")
    )

    t4 = b.add("58:55", 2, "tackle", "RK", "RK-4", [36.0, 38.0], "won_possession")
    turnover_ids.append(t4)
    pressure_ids.append(
        b.add("59:10", 2, "pressure", "RK", "RK-8", [44.0, 52.0], "applied")
    )

    # Shot after turnovers (~60')
    link = b.add("60:05", 2, "pass", "RK", "RK-8", [55.0, 48.0], "complete", related=[t4])
    shot_to = b.add(
        "60:18",
        2,
        "shot",
        "RK",
        "RK-9",
        [78.0, 50.0],
        "saved",
        related=[link, *turnover_ids[-3:]],
        attrs={"xg": 0.21},
    )
    b.add("60:19", 2, "save", "BH", "BH-1", [2.0, 50.0], "parried", related=[shot_to])

    t5 = b.add("61:30", 2, "tackle", "RK", "RK-4", [32.0, 47.0], "won_possession")
    turnover_ids.append(t5)
    pressure_ids.append(
        b.add("61:45", 2, "pressure", "RK", "RK-6", [38.0, 45.0], "applied")
    )

    # Equaliser ~63'
    assist = b.add("62:48", 2, "pass", "RK", "RK-10", [74.0, 58.0], "complete")
    equaliser = b.add(
        "63:02",
        2,
        "shot",
        "RK",
        "RK-9",
        [86.0, 48.0],
        "goal",
        related=[assist, t5],
        attrs={"xg": 0.38, "body_part": "header"},
    )
    b.add("63:03", 2, "save", "BH", "BH-1", [1.0, 50.0], "conceded", related=[equaliser])

    # Momentum continues briefly
    for minute in (65, 68, 71):
        _pass_chain(
            b,
            minute,
            10,
            2,
            "RK",
            ["RK-5", "RK-8", "RK-10", "RK-7"],
            [48.0, 58.0, 68.0, 78.0],
            complete=True,
        )

    b.add("70:22", 2, "shot", "BH", "BH-9", [82.0, 44.0], "blocked")
    b.add("74:01", 2, "shot", "RK", "RK-7", [80.0, 36.0], "off_target")

    # Player milestone: RK-4 fifth won tackle of the match (late)
    # Count: t1,t3,t4,t5 already; add one more successful tackle earlier mid spells...
    # We have t1,t3,t4,t5 = 4. Add one between 58-59 already have 4. Need 5th:
    # Actually: t1 (55:18), t3 (57:22), t4 (58:55), t5 (61:30) = 4. Add mid-spell one:
    # Wait we need 5th late - add tackle at 78'
    milestone_tackle = b.add(
        "78:14",
        2,
        "tackle",
        "RK",
        "RK-4",
        [41.0, 50.0],
        "won_possession",
        attrs={"milestone": "5th_tackle_won", "career_note": "match_high"},
    )

    # Closing exchanges
    for minute in (80, 84, 88):
        team = "BH" if minute in (80, 88) else "RK"
        plist = (
            ["BH-6", "BH-8", "BH-10", "BH-11"]
            if team == "BH"
            else ["RK-6", "RK-8", "RK-5", "RK-11"]
        )
        xs = [45.0, 55.0, 65.0, 72.0] if team == "BH" else [60.0, 50.0, 40.0, 32.0]
        _pass_chain(b, minute, 15, 2, team, plist, xs, complete=True)

    b.add("90:00", 2, "period_end", "RK", None, None, "ended")

    doc = {
        "schema_version": SCHEMA_VERSION,
        "match": {
            "id": MATCH_ID,
            "competition": "Harbor League (synthetic)",
            "kickoff": "2026-10-17T15:00:00+03:00",
            "venue": "Seaside Synthetic Arena",
            "home": home,
            "away": away,
            "score_ht": [1, 0],
            "score_ft": [1, 1],
            "seed": None,
            "notes": (
                "Hand-scripted demo match. BH 1-0 HT; RK press from 55'; "
                "equaliser 63'; RK-4 5th tackle won milestone 78'."
            ),
        },
        "events": b.events,
        # Planted id hints for fixture authors / detector tests (not required by schema)
        "_planted": {
            "bh_goal": shot,
            "pressure_event_ids": pressure_ids,
            "turnover_event_ids": turnover_ids,
            "shot_after_turnovers": shot_to,
            "equaliser": equaliser,
            "milestone_tackle": milestone_tackle,
            "milestone_player": "RK-4",
        },
    }
    return doc


def build_demo_match_public() -> dict[str, Any]:
    """Match document without internal `_planted` hints (API-safe)."""
    doc = build_demo_match()
    public = deepcopy(doc)
    public.pop("_planted", None)
    return public

"""Kiswahili narrator. Builds sentences directly from moment facts using lexicon terms;
it never translates the English narrative. Lines are pending native-speaker review."""

from __future__ import annotations

from typing import Any

from agents.persona.compose import LanguageTemplates, Piece, compose
from agents.persona.definitions import get_persona
from agents.persona.facts import MomentFacts, build_facts, player_name
from lexicon import load_lexicon

SW_NUMBER_WORDS = {
    1: "moja",
    2: "mbili",
    3: "tatu",
    4: "nne",
    5: "tano",
    6: "sita",
    7: "saba",
    8: "nane",
    9: "tisa",
    10: "kumi",
}

_SHOT_OUTCOME = {
    "saved": "kipa analiokoa",
    "goal": "linaingia wavuni",
    "blocked": "linazuiwa",
    "off_target": "linatoka nje ya lango",
    "woodwork": "linagonga mwamba",
}


def sw_count(n: int) -> str:
    """Small counts as words (mara nne); larger ones stay digits."""
    return SW_NUMBER_WORDS.get(n, str(n))


def _score(f: MomentFacts, key: str) -> str:
    home, away = f.stats[key]
    return f"{home}–{away}"


def _shooter(f: MomentFacts) -> tuple[str, dict[str, str]]:
    pid = f.entities.get("shooter")
    return player_name(f.match_meta, pid), {"shooter": pid}


# --- pressure_spell -------------------------------------------------------------------------

def _press_formal(f: MomentFacts) -> Piece:
    return Piece(
        f"Kati ya dakika ya {f.minute_start} na {f.minute_end}, {f.team_name} wanawabana "
        f"{f.opponent_name} katika nusu yao ya uwanja na kuwanyang'anya mpira mara kwa mara."
    )


def _press_casual(f: MomentFacts) -> Piece:
    return Piece(
        f"{f.team_name} wanawabana {f.opponent_name} vilivyo! {f.opponent_name} wanapoteza mpira "
        f"karibu na lango lao tena na tena."
    )


def _press_simple(f: MomentFacts) -> Piece:
    return Piece(
        f"{f.team_name} wanawabana {f.opponent_name}: wanawakimbilia karibu na lango lao ili "
        f"kuwanyang'anya mpira haraka."
    )


def _press_stats(f: MomentFacts) -> Piece:
    s = f.stats
    return Piece(
        f"Takwimu: {f.team_name} wamenyakua mpira mara {sw_count(s['high_turnovers'])} na kuweka "
        f"shinikizo mara {sw_count(s['pressure_events'])} katika nusu ya {f.opponent_name}.",
        stats_used={k: s[k] for k in ("high_turnovers", "pressure_events")},
    )


# --- shot_after_turnovers -------------------------------------------------------------------

def _shot_formal(f: MomentFacts) -> Piece:
    name, ent = _shooter(f)
    return Piece(
        f"Baada ya kunyang'anya mpira katika nusu ya {f.opponent_name}, {f.team_name} wanapata "
        f"nafasi: {name} anapiga shuti, na {_SHOT_OUTCOME[f.stats['shot_outcome']]}.",
        stats_used={"shot_outcome": f.stats["shot_outcome"]},
        entities_used=ent,
    )


def _shot_casual(f: MomentFacts) -> Piece:
    name, ent = _shooter(f)
    return Piece(
        f"Presha inazaa matunda! {f.team_name} wananyang'anya mpira, na {name} anapiga shuti — "
        f"{_SHOT_OUTCOME[f.stats['shot_outcome']]}!",
        stats_used={"shot_outcome": f.stats["shot_outcome"]},
        entities_used=ent,
    )


def _shot_simple(f: MomentFacts) -> Piece:
    name, ent = _shooter(f)
    return Piece(
        f"{f.team_name} wamenyang'anya mpira karibu na lango la {f.opponent_name}, na {name} "
        f"amepiga shuti haraka, na {_SHOT_OUTCOME[f.stats['shot_outcome']]}.",
        stats_used={"shot_outcome": f.stats["shot_outcome"]},
        entities_used=ent,
    )


def _shot_stats(f: MomentFacts) -> Piece:
    n = f.stats["turnovers_before_shot"]
    return Piece(
        f"Takwimu: {f.team_name} walinyakua mpira mara {sw_count(n)} kabla ya shuti hili.",
        stats_used={"turnovers_before_shot": n},
    )


# --- momentum_swing -------------------------------------------------------------------------

def _swing_formal(f: MomentFacts) -> Piece:
    return Piece(
        f"Mwelekeo wa mchezo umebadilika. Kwa kuwabana {f.opponent_name}, {f.team_name} wamegeuza "
        f"matokeo kutoka {_score(f, 'score_before')} hadi {_score(f, 'score_after')}.",
        stats_used={k: f.stats[k] for k in ("score_before", "score_after")},
    )


def _swing_casual(f: MomentFacts) -> Piece:
    return Piece(
        f"Upepo wa mchezo umegeuka! Presha ya {f.team_name} imelipa, na sasa ni "
        f"{_score(f, 'score_after')}.",
        stats_used={"score_after": f.stats["score_after"]},
    )


def _swing_simple(f: MomentFacts) -> Piece:
    return Piece(
        f"Mwelekeo wa mchezo umebadilika: {f.team_name} waliendelea kuwabana {f.opponent_name}, na "
        f"matokeo yamebadilika kutoka {_score(f, 'score_before')} hadi {_score(f, 'score_after')}.",
        stats_used={k: f.stats[k] for k in ("score_before", "score_after")},
    )


def _swing_stats(f: MomentFacts) -> Piece:
    key = f.turnovers_key()
    return Piece(
        f"Takwimu: {f.team_name} walinyakua mpira mara {sw_count(f.stats[key])} katika kipindi "
        f"hicho cha presha.",
        stats_used={key: f.stats[key]},
    )


# --- goal -----------------------------------------------------------------------------------

def _goal_parts(f: MomentFacts) -> tuple[str, dict[str, Any], dict[str, str]]:
    pid = f.stats["scorer"]
    return (
        player_name(f.match_meta, pid),
        {k: f.stats[k] for k in ("scorer", "minute", "score_after")},
        {"scorer": pid},
    )


def _goal_formal(f: MomentFacts) -> Piece:
    name, used, ent = _goal_parts(f)
    h, a = f.stats["score_after"]
    minute = f.stats["minute"]
    action = {
        "level": f"anafunga bao la kusawazisha kwa {f.team_name}",
        "ahead": f"anafunga bao, na {f.team_name} wanaongoza",
        "behind": f"anafunga bao kwa {f.team_name}, lakini bado wako nyuma",
    }[f.goal_situation()]
    return Piece(
        f"Dakika ya {minute}, {name} {action}. Matokeo sasa ni {f.home_name} {h}–{a} {f.away_name}.",
        used,
        ent,
    )


def _goal_casual(f: MomentFacts) -> Piece:
    name, used, ent = _goal_parts(f)
    h, a = f.stats["score_after"]
    opener = f"Goooli! {name} anatikisa nyavu dakika ya {f.stats['minute']}!"
    follow = {
        "level": f"{f.team_name} wamesawazisha, sasa ni {h}–{a}. Mchezo upya!",
        "ahead": f"{f.team_name} wanaongoza, sasa ni {h}–{a}!",
        "behind": f"{f.team_name} wanapunguza pengo, sasa ni {h}–{a}!",
    }[f.goal_situation()]
    return Piece(f"{opener} {follow}", used, ent)


def _goal_simple(f: MomentFacts) -> Piece:
    name, used, ent = _goal_parts(f)
    h, a = f.stats["score_after"]
    text = (
        f"{name} amefunga bao kwa {f.team_name} katika dakika ya {f.stats['minute']}. Sasa "
        f"matokeo ni {f.home_name} {h}, {f.away_name} {a}."
    )
    if f.goal_situation() == "level":
        text += " Sasa ni sare."
    return Piece(text, used, ent)


def _goal_stats(f: MomentFacts) -> Piece:
    name, used, ent = _goal_parts(f)
    return Piece(
        f"Takwimu: mfungaji ni {name}, dakika ya {f.stats['minute']}, matokeo baada ya bao "
        f"{_score(f, 'score_after')}.",
        used,
        ent,
    )


# --- player_milestone -----------------------------------------------------------------------

def _milestone_parts(f: MomentFacts) -> tuple[str, int, dict[str, str]]:
    pid = f.stats["player"]
    return player_name(f.match_meta, pid), f.stats["value"], {"player": pid}


def _milestone_formal(f: MomentFacts) -> Piece:
    name, value, ent = _milestone_parts(f)
    return Piece(
        f"Dakika ya {f.minute_peak}, {name} wa {f.team_name} anakaba kwa mafanikio kwa mara ya "
        f"{sw_count(value)} katika mchezo huu.",
        {"value": value},
        ent,
    )


def _milestone_casual(f: MomentFacts) -> Piece:
    name, value, ent = _milestone_parts(f)
    return Piece(
        f"{name} ni ukuta! Amekaba kwa mafanikio mara {sw_count(value)} leo.", {"value": value}, ent
    )


def _milestone_simple(f: MomentFacts) -> Piece:
    name, value, ent = _milestone_parts(f)
    return Piece(
        f"{name} wa {f.team_name} amemnyang'anya mpinzani mpira kwa kukaba mara {sw_count(value)}.",
        {"value": value},
        ent,
    )


def _milestone_stats(f: MomentFacts) -> Piece:
    name, value, ent = _milestone_parts(f)
    return Piece(
        f"Takwimu: {name} amekaba kwa mafanikio mara {sw_count(value)} katika mchezo huu, hatua "
        f"muhimu kwake.",
        {"metric": f.stats["metric"], "value": value},
        ent,
    )


TEMPLATES = LanguageTemplates(
    language="sw",
    core={
        "pressure_spell": {"formal": _press_formal, "casual": _press_casual, "simple": _press_simple},
        "shot_after_turnovers": {
            "formal": _shot_formal,
            "casual": _shot_casual,
            "simple": _shot_simple,
        },
        "momentum_swing": {"formal": _swing_formal, "casual": _swing_casual, "simple": _swing_simple},
        "goal": {"formal": _goal_formal, "casual": _goal_casual, "simple": _goal_simple},
        "player_milestone": {
            "formal": _milestone_formal,
            "casual": _milestone_casual,
            "simple": _milestone_simple,
        },
    },
    stats={
        "pressure_spell": _press_stats,
        "shot_after_turnovers": _shot_stats,
        "momentum_swing": _swing_stats,
        "goal": _goal_stats,
        "player_milestone": _milestone_stats,
    },
)


def narrate_sw(
    moment: dict[str, Any],
    match_meta: dict[str, Any],
    persona_id: str,
    register: str | None = None,
) -> dict[str, Any]:
    """Kiswahili narrative for one moment and persona."""
    facts = build_facts(moment, match_meta)
    return compose(facts, get_persona(persona_id), register, TEMPLATES, load_lexicon())

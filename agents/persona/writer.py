"""English persona writer. Deterministic templates; a Foundry model can replace these
behind ``write_en`` as long as it returns the same narrative shape."""

from __future__ import annotations

from typing import Any

from agents.persona.compose import LanguageTemplates, Piece, compose
from agents.persona.definitions import get_persona
from agents.persona.facts import MomentFacts, build_facts, player_name
from lexicon import load_lexicon

_SHOT_OUTCOME = {
    "saved": "the goalkeeper saved it",
    "goal": "it went in",
    "blocked": "it was blocked",
    "off_target": "it went wide",
    "woodwork": "it hit the woodwork",
}
_SHOT_OUTCOME_SHORT = {
    "saved": "saved",
    "goal": "scored",
    "blocked": "blocked",
    "off_target": "off target",
    "woodwork": "off the woodwork",
}


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _score(f: MomentFacts, key: str) -> str:
    home, away = f.stats[key]
    return f"{home}–{away}"


def _shooter(f: MomentFacts) -> tuple[str, dict[str, str]]:
    pid = f.entities.get("shooter")
    return player_name(f.match_meta, pid), {"shooter": pid}


# --- pressure_spell -------------------------------------------------------------------------

def _press_formal(f: MomentFacts) -> Piece:
    return Piece(
        f"Between {f.minute_start}' and {f.minute_end}', {f.team_name} pressed high and won the "
        f"ball repeatedly in the {f.opponent_name} half."
    )


def _press_casual(f: MomentFacts) -> Piece:
    return Piece(
        f"{f.opponent_name} keep giving the ball away near their own goal, and {f.team_name} can "
        f"smell a chance. The press is on!"
    )


def _press_simple(f: MomentFacts) -> Piece:
    return Piece(
        f"{f.team_name} are pressing: they chase {f.opponent_name} close to their own goal to win "
        f"the ball back quickly."
    )


def _press_stats(f: MomentFacts) -> Piece:
    s = f.stats
    return Piece(
        f"{f.team_name} forced {s['high_turnovers']} turnovers and made {s['pressure_events']} "
        f"pressure actions in the {f.opponent_name} half over {s['window_minutes']} minutes.",
        stats_used={k: s[k] for k in ("high_turnovers", "pressure_events", "window_minutes")},
    )


# --- shot_after_turnovers -------------------------------------------------------------------

def _shot_formal(f: MomentFacts) -> Piece:
    name, ent = _shooter(f)
    outcome = _SHOT_OUTCOME[f.stats["shot_outcome"]]
    return Piece(
        f"After winning the ball back in the {f.opponent_name} half, {f.team_name} created a "
        f"chance: {name} took a shot and {outcome}.",
        stats_used={"shot_outcome": f.stats["shot_outcome"]},
        entities_used=ent,
    )


def _shot_casual(f: MomentFacts) -> Piece:
    name, ent = _shooter(f)
    outcome = _SHOT_OUTCOME[f.stats["shot_outcome"]]
    return Piece(
        f"The press pays off: {f.team_name} win the ball and {name} gets a shot away — {outcome}!",
        stats_used={"shot_outcome": f.stats["shot_outcome"]},
        entities_used=ent,
    )


def _shot_simple(f: MomentFacts) -> Piece:
    name, ent = _shooter(f)
    outcome = _SHOT_OUTCOME[f.stats["shot_outcome"]]
    return Piece(
        f"{f.team_name} won the ball near the {f.opponent_name} goal, and {name} quickly took a "
        f"shot — {outcome}.",
        stats_used={"shot_outcome": f.stats["shot_outcome"]},
        entities_used=ent,
    )


def _shot_stats(f: MomentFacts) -> Piece:
    s = f.stats
    return Piece(
        f"{s['turnovers_before_shot']} turnovers came before the shot, which was "
        f"{_SHOT_OUTCOME_SHORT[s['shot_outcome']]}.",
        stats_used={k: s[k] for k in ("turnovers_before_shot", "shot_outcome")},
    )


# --- momentum_swing -------------------------------------------------------------------------

def _swing_formal(f: MomentFacts) -> Piece:
    return Piece(
        f"Momentum has swung: by pressing {f.opponent_name}, {f.team_name} turned the score from "
        f"{_score(f, 'score_before')} to {_score(f, 'score_after')}.",
        stats_used={k: f.stats[k] for k in ("score_before", "score_after")},
    )


def _swing_casual(f: MomentFacts) -> Piece:
    return Piece(
        f"What a turnaround! The {f.team_name} press flipped the game, and it's "
        f"{_score(f, 'score_after')} now.",
        stats_used={"score_after": f.stats["score_after"]},
    )


def _swing_simple(f: MomentFacts) -> Piece:
    return Piece(
        f"The momentum changed: {f.team_name} kept pressing {f.opponent_name}, and the score went "
        f"from {_score(f, 'score_before')} to {_score(f, 'score_after')}.",
        stats_used={k: f.stats[k] for k in ("score_before", "score_after")},
    )


def _swing_stats(f: MomentFacts) -> Piece:
    key = f.turnovers_key()
    return Piece(
        f"{f.team_name} won the ball {f.stats[key]} times in the spell before the goal.",
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
    action = {
        "level": f"scores the equaliser for {f.team_name}",
        "ahead": f"scores to put {f.team_name} ahead",
        "behind": f"scores for {f.team_name} to pull one back",
    }[f.goal_situation()]
    return Piece(
        f"{f.stats['minute']}': {name} {action}. It is {f.home_name} {h}–{a} {f.away_name}.",
        used,
        ent,
    )


def _goal_casual(f: MomentFacts) -> Piece:
    name, used, ent = _goal_parts(f)
    h, a = f.stats["score_after"]
    line = {
        "level": f"GOAL! {name} levels it for {f.team_name} — {h}–{a} and game on!",
        "ahead": f"GOAL! {name} puts {f.team_name} in front — {h}–{a}!",
        "behind": f"GOAL! {name} pulls one back for {f.team_name} — {h}–{a}!",
    }[f.goal_situation()]
    return Piece(line, {k: used[k] for k in ("scorer", "score_after")}, ent)


def _goal_simple(f: MomentFacts) -> Piece:
    name, used, ent = _goal_parts(f)
    h, a = f.stats["score_after"]
    text = (
        f"{name} scored a goal for {f.team_name} in minute {f.stats['minute']}. The score is now "
        f"{f.home_name} {h}, {f.away_name} {a}."
    )
    if f.goal_situation() == "level":
        text += " The teams are level."
    return Piece(text, used, ent)


def _goal_stats(f: MomentFacts) -> Piece:
    name, used, ent = _goal_parts(f)
    return Piece(
        f"Scorer: {name}, {f.stats['minute']}'. Score after the goal: {_score(f, 'score_after')}.",
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
        f"{f.minute_peak}': {name} of {f.team_name} wins a {_ordinal(value)} tackle of the match.",
        {"value": value},
        ent,
    )


def _milestone_casual(f: MomentFacts) -> Piece:
    name, value, ent = _milestone_parts(f)
    return Piece(f"{name} is a wall! That's tackle number {value} today.", {"value": value}, ent)


def _milestone_simple(f: MomentFacts) -> Piece:
    name, value, ent = _milestone_parts(f)
    return Piece(
        f"{name} from {f.team_name} has now won the ball with a tackle {value} times.",
        {"value": value},
        ent,
    )


def _milestone_stats(f: MomentFacts) -> Piece:
    name, value, ent = _milestone_parts(f)
    return Piece(
        f"Tackles won by {name}: {value}, a match milestone.",
        {"metric": f.stats["metric"], "value": value},
        ent,
    )


TEMPLATES = LanguageTemplates(
    language="en",
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


def write_en(
    moment: dict[str, Any],
    match_meta: dict[str, Any],
    persona_id: str,
    register: str | None = None,
) -> dict[str, Any]:
    """English narrative for one moment and persona. Numbers come only from ``moment['stats']``."""
    facts = build_facts(moment, match_meta)
    return compose(facts, get_persona(persona_id), register, TEMPLATES, load_lexicon())

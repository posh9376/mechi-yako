"""Compose a narrative from language templates: story core, analyst stats, newcomer gloss."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from agents.persona.definitions import Persona
from agents.persona.facts import MomentFacts, UnsupportedMoment
from lexicon import Lexicon


@dataclass
class Piece:
    text: str
    stats_used: dict[str, Any] = field(default_factory=dict)
    entities_used: dict[str, str] = field(default_factory=dict)


Template = Callable[[MomentFacts], Piece]


@dataclass(frozen=True)
class LanguageTemplates:
    language: str
    core: dict[str, dict[str, Template]]
    stats: dict[str, Template]

    def registers(self, moment_type: str) -> tuple[str, ...]:
        return tuple(self.core.get(moment_type, {}))


def resolve_register(templates: LanguageTemplates, moment_type: str, wanted: str) -> str:
    """Use ``wanted`` if this language has it for the moment type, else fall back to formal."""
    by_register = templates.core.get(moment_type)
    if not by_register:
        raise UnsupportedMoment(f"no {templates.language} templates for moment type {moment_type!r}")
    if wanted in by_register:
        return wanted
    return "formal"


def compose(
    facts: MomentFacts,
    persona: Persona,
    register: str | None,
    templates: LanguageTemplates,
    lexicon: Lexicon,
) -> dict[str, Any]:
    requested = register or persona.default_register
    used_register = resolve_register(templates, facts.type, requested)

    pieces = [templates.core[facts.type][used_register](facts)]
    if persona.include_stats:
        pieces.append(templates.stats[facts.type](facts))

    lexicon_terms = list(lexicon.required_terms(facts.type))
    if persona.include_gloss and lexicon_terms:
        gloss = lexicon.term(lexicon_terms[0]).gloss(templates.language)
        if gloss:
            pieces.append(Piece(text=gloss))

    stats_used: dict[str, Any] = {}
    entities_used: dict[str, str] = {}
    for piece in pieces:
        stats_used.update(piece.stats_used)
        entities_used.update(piece.entities_used)

    return {
        "moment_id": facts.moment["id"],
        "match_id": facts.moment["match_id"],
        "moment_type": facts.type,
        "text": " ".join(p.text for p in pieces),
        "language": templates.language,
        "persona": persona.id,
        "register": used_register,
        "register_requested": requested,
        "event_ids": list(facts.moment["event_ids"]),
        "stats_used": stats_used,
        "entities_used": entities_used,
        "lexicon_terms": lexicon_terms,
        "writer": f"deterministic-{templates.language}-v1",
    }

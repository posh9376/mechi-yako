"""Narration pipeline: verify the moment's claims, write for the persona, then run language QA."""

from __future__ import annotations

from typing import Any

from agents.language_qa import check_narrative
from agents.narrator.sw import TEMPLATES as SW_TEMPLATES
from agents.narrator.sw import narrate_sw
from agents.persona.definitions import LANGUAGES, PERSONAS, REGISTERS
from agents.persona.facts import UnsupportedMoment
from agents.persona.writer import TEMPLATES as EN_TEMPLATES
from agents.persona.writer import write_en
from api.claims import ClaimChecker, apply_verification, verify_moment
from lexicon import load_lexicon

WRITERS = {"en": write_en, "sw": narrate_sw}
TEMPLATES = {"en": EN_TEMPLATES, "sw": SW_TEMPLATES}


class NarrationError(ValueError):
    pass


def options() -> dict[str, Any]:
    lexicon = load_lexicon()
    return {
        "personas": [p.to_dict() for p in PERSONAS.values()],
        "languages": list(LANGUAGES),
        "registers": {
            lang: [r for r in REGISTERS if any(r in by_reg for by_reg in t.core.values())]
            for lang, t in TEMPLATES.items()
        },
        "lexicon": {"version": lexicon.version, "terms": len(lexicon.terms), "review": lexicon.review_status},
    }


def narrate(
    moment: dict[str, Any],
    doc: dict[str, Any],
    *,
    persona: str,
    language: str,
    register: str | None,
    checker: ClaimChecker,
) -> dict[str, Any]:
    if persona not in PERSONAS:
        raise NarrationError(f"unknown persona {persona!r}")
    if language not in WRITERS:
        raise NarrationError(f"unsupported language {language!r}")
    if register is not None and register not in REGISTERS:
        raise NarrationError(f"unknown register {register!r}")

    decisions = verify_moment(moment, doc, checker)
    verified, blocked = apply_verification(moment, decisions)
    try:
        narrative = WRITERS[language](verified, doc["match"], persona, register)
    except KeyError as exc:
        raise NarrationError(f"cannot narrate: stat {exc} was blocked by verification") from None
    except UnsupportedMoment as exc:
        raise NarrationError(str(exc)) from None

    qa = check_narrative(narrative, verified)
    return {
        "narrative": narrative,
        "qa": qa,
        "verification": {
            "approved": sum(d["status"] == "approved" for d in decisions),
            "corrected": [d for d in decisions if d["status"] == "corrected"],
            "blocked": blocked,
        },
    }

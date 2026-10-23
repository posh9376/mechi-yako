"""Narration pipeline: explain → verify → persona/Kiswahili write → language QA.

The explainer builds structured claims (template numbers, optional Foundry
sentences). The claim checker verifies them and the fact-layer stats used by
the persona and Kiswahili writers. Both land in the HTTP response so the Why?
panel can show explainer output (not only the CLI).
"""

from __future__ import annotations

from typing import Any

from agents.foundry import make_explainer
from agents.language_qa import check_narrative
from agents.narrator.sw import TEMPLATES as SW_TEMPLATES
from agents.narrator.sw import narrate_sw
from agents.persona.definitions import LANGUAGES, PERSONAS, REGISTERS
from agents.persona.facts import UnsupportedMoment
from agents.persona.writer import TEMPLATES as EN_TEMPLATES
from agents.persona.writer import write_en
from api.claims import Claim, ClaimChecker, apply_verification, verify_moment
from api.explanations import ExplanationCache
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


def explain_moment(
    moment: dict[str, Any],
    doc: dict[str, Any],
    checker: ClaimChecker,
    *,
    source: str = "live",
    cache: ExplanationCache | None = None,
) -> dict[str, Any]:
    """Run the explainer (through ``cache`` when given) and verify each emitted claim."""
    match_id = doc["match"]["id"]
    if cache is not None:
        package = cache.package(match_id, source, moment)
    else:
        package = make_explainer(match_id).explain_moment(moment)
    verifications: list[dict[str, Any]] = []
    for raw in package["claims"]:
        claim = Claim(
            moment_id=moment["id"],
            metric=raw["metric"],
            value=raw["value"],
            event_ids=tuple(raw.get("event_ids") or moment.get("event_ids") or ()),
        )
        decision = checker.check(claim, moment, doc)
        decision["sentence"] = raw.get("sentence")
        decision["claim_id"] = raw.get("id")
        verifications.append(decision)
    return {
        **package,
        "verifications": verifications,
        "summary": {
            status: sum(v["status"] == status for v in verifications)
            for status in ("approved", "corrected", "blocked")
        },
        "explainer": package.get("explainer") or "template-v1",
    }


def narrate(
    moment: dict[str, Any],
    doc: dict[str, Any],
    *,
    persona: str,
    language: str,
    register: str | None,
    checker: ClaimChecker,
    explain: bool = True,
    source: str = "live",
    cache: ExplanationCache | None = None,
) -> dict[str, Any]:
    """Verified narrative plus QA. With ``explain=False`` the Why? panel package is left
    out, so the response never waits on the explainer model."""
    if persona not in PERSONAS:
        raise NarrationError(f"unknown persona {persona!r}")
    if language not in WRITERS:
        raise NarrationError(f"unsupported language {language!r}")
    if register is not None and register not in REGISTERS:
        raise NarrationError(f"unknown register {register!r}")

    # Fact-layer stats → verify → Eric's persona/Kiswahili writers (UI copy)
    decisions = verify_moment(moment, doc, checker)
    verified, blocked = apply_verification(moment, decisions)
    try:
        narrative = WRITERS[language](verified, doc["match"], persona, register)
    except KeyError as exc:
        raise NarrationError(f"cannot narrate: stat {exc} was blocked by verification") from None
    except UnsupportedMoment as exc:
        raise NarrationError(str(exc)) from None

    qa = check_narrative(narrative, verified)
    result: dict[str, Any] = {
        "narrative": narrative,
        "qa": qa,
        "verification": {
            "approved": sum(d["status"] == "approved" for d in decisions),
            "corrected": [d for d in decisions if d["status"] == "corrected"],
            "blocked": blocked,
        },
    }
    if explain:
        # Explainer package for the Why? panel (same checker)
        result["explanation"] = explain_moment(moment, doc, checker, source=source, cache=cache)
    return result

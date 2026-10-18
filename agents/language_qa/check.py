"""Deterministic language QA.

Flags a narrative when:
- a number in the text is not backed by the moment's stats or clock,
- ``stats_used`` disagrees with the moment,
- it cites event ids the moment does not have,
- it names an entity the moment does not reference,
- a required lexicon term for the moment type is missing,
- Kiswahili text contains English function words (translation leakage).

A model back-translation check can be added behind ``check_narrative`` later; the result
shape stays ``{"status": "pass" | "flag", "reasons": [...]}``.
"""

from __future__ import annotations

import re
from typing import Any

from lexicon import Lexicon, load_lexicon
from pipeline.clock import parse_clock

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_EVENT_ID = re.compile(r"^e-\d+$")

NUMBER_WORDS = {
    "en": {
        "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    },
    "sw": {
        "moja": 1, "mbili": 2, "tatu": 3, "nne": 4, "tano": 5,
        "sita": 6, "saba": 7, "nane": 8, "tisa": 9, "kumi": 10,
    },
}

_ENGLISH_FUNCTION_WORDS = {"the", "and", "with", "after", "for", "has", "is", "was", "it", "of"}


def _flatten_numbers(value: Any) -> set[float]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, (int, float)):
        return {float(value)}
    if isinstance(value, (list, tuple)):
        out: set[float] = set()
        for v in value:
            out |= _flatten_numbers(v)
        return out
    if isinstance(value, str) and not _EVENT_ID.match(value):
        return {float(n) for n in _NUMBER.findall(value)}
    return set()


def allowed_numbers(moment: dict[str, Any]) -> set[float]:
    allowed: set[float] = set()
    for value in moment["stats"].values():
        allowed |= _flatten_numbers(value)
    for key in ("t_start", "t_end", "t_peak"):
        allowed.add(float(parse_clock(moment[key]) // 60))
    return allowed


def numbers_in_text(text: str, language: str) -> list[float]:
    found = [float(n) for n in _NUMBER.findall(text)]
    words = NUMBER_WORDS.get(language, {})
    for token in re.findall(r"[a-zA-Z']+", text.lower()):
        if token in words:
            found.append(float(words[token]))
    return found


def _entity_ids(moment: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for source in (moment.get("entities") or {}, moment["stats"]):
        for value in source.values():
            if isinstance(value, str):
                ids.add(value)
    return ids


def check_narrative(
    narrative: dict[str, Any],
    moment: dict[str, Any],
    lexicon: Lexicon | None = None,
) -> dict[str, Any]:
    lexicon = lexicon or load_lexicon()
    language = narrative["language"]
    text = narrative["text"]
    reasons: list[str] = []

    if narrative.get("moment_id") != moment["id"]:
        reasons.append(f"narrative is for {narrative.get('moment_id')!r}, not {moment['id']!r}")

    cited = narrative.get("event_ids") or []
    if not cited:
        reasons.append("narrative cites no events")
    foreign = [e for e in cited if e not in set(moment["event_ids"])]
    if foreign:
        reasons.append(f"cites events not in the moment: {foreign}")

    for key, value in (narrative.get("stats_used") or {}).items():
        if key not in moment["stats"]:
            reasons.append(f"stat {key!r} is not in the fact layer")
        elif moment["stats"][key] != value:
            reasons.append(f"stat {key!r} is {value!r} but the fact layer says {moment['stats'][key]!r}")

    allowed = allowed_numbers(moment)
    unbacked = sorted({n for n in numbers_in_text(text, language) if n not in allowed})
    if unbacked:
        pretty = [int(n) if n.is_integer() else n for n in unbacked]
        reasons.append(f"numbers not backed by the fact layer: {pretty}")

    known_entities = _entity_ids(moment)
    for role, entity_id in (narrative.get("entities_used") or {}).items():
        if entity_id not in known_entities:
            reasons.append(f"{role} {entity_id!r} is not referenced by the moment")

    present = lexicon.find_terms(text, language)
    missing = [t for t in lexicon.required_terms(moment["type"]) if t not in present]
    if missing:
        reasons.append(f"missing required {language} terms: {missing}")

    if language == "sw":
        tokens = set(re.findall(r"[a-z']+", text.lower()))
        leaked = sorted(tokens & _ENGLISH_FUNCTION_WORDS)
        if leaked:
            reasons.append(f"English words in Kiswahili text: {leaked}")

    return {"status": "flag" if reasons else "pass", "reasons": reasons}

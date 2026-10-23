"""Kiswahili football lexicon. Data lives in ``sw.yaml``."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

LEXICON_PATH = Path(__file__).resolve().parent / "sw.yaml"


@dataclass(frozen=True)
class Term:
    id: str
    en: str
    sw: str
    sw_forms: tuple[str, ...]
    en_forms: tuple[str, ...]
    gloss_en: str | None = None
    gloss_sw: str | None = None
    formal: str | None = None
    review: str = "pending"

    def forms(self, language: str) -> tuple[str, ...]:
        return self.sw_forms if language == "sw" else self.en_forms

    def gloss(self, language: str) -> str | None:
        return self.gloss_sw if language == "sw" else self.gloss_en


@dataclass(frozen=True)
class Lexicon:
    version: int
    review_status: str
    terms: dict[str, Term]
    moment_terms: dict[str, tuple[str, ...]]
    registers: dict[str, dict[str, Any]] = field(default_factory=dict)

    def term(self, term_id: str) -> Term:
        return self.terms[term_id]

    def required_terms(self, moment_type: str) -> tuple[str, ...]:
        return self.moment_terms.get(moment_type, ())

    def find_terms(self, text: str, language: str) -> set[str]:
        """Term ids whose accepted forms appear in ``text`` (case-insensitive)."""
        lowered = text.lower()
        return {
            t.id
            for t in self.terms.values()
            if any(form.lower() in lowered for form in t.forms(language))
        }


def _parse(raw: dict[str, Any]) -> Lexicon:
    terms: dict[str, Term] = {}
    for entry in raw.get("terms", []):
        term = Term(
            id=entry["id"],
            en=entry["en"],
            sw=entry["sw"],
            sw_forms=tuple(entry.get("sw_forms") or [entry["sw"]]),
            en_forms=tuple(entry.get("en_forms") or [entry["en"]]),
            gloss_en=entry.get("gloss_en"),
            gloss_sw=entry.get("gloss_sw"),
            formal=entry.get("formal"),
            review=entry.get("review", "pending"),
        )
        if term.id in terms:
            raise ValueError(f"duplicate lexicon term id {term.id!r}")
        terms[term.id] = term

    moment_terms = {k: tuple(v) for k, v in (raw.get("moment_terms") or {}).items()}
    for moment_type, ids in moment_terms.items():
        missing = [i for i in ids if i not in terms]
        if missing:
            raise ValueError(f"moment_terms[{moment_type}] references unknown terms {missing}")

    return Lexicon(
        version=int(raw.get("version", 1)),
        review_status=(raw.get("review") or {}).get("status", "pending"),
        terms=terms,
        moment_terms=moment_terms,
        registers=raw.get("registers") or {},
    )


@lru_cache(maxsize=4)
def load_lexicon(path: str | Path = LEXICON_PATH) -> Lexicon:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return _parse(raw)

"""The three viewer personas. Personas change depth and vocabulary, never facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass

REGISTERS = ("formal", "casual", "simple")
LANGUAGES = ("en", "sw")


@dataclass(frozen=True)
class Persona:
    id: str
    label: str
    description: str
    include_stats: bool
    include_gloss: bool
    default_register: str
    keeps: tuple[str, ...]
    omits: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


PERSONAS: dict[str, Persona] = {
    "analyst": Persona(
        id="analyst",
        label="Analyst",
        description="Wants the numbers behind the moment: counts, windows and zones.",
        include_stats=True,
        include_gloss=False,
        default_register="formal",
        keeps=("story", "counts", "time_windows", "zones", "scoreline"),
        omits=("term_glosses",),
    ),
    "casual": Persona(
        id="casual",
        label="Casual fan",
        description="Wants the story and the feeling of the moment, not a stats sheet.",
        include_stats=False,
        include_gloss=False,
        default_register="casual",
        keeps=("story", "scoreline", "names"),
        omits=("counts", "time_windows", "term_glosses"),
    ),
    "newcomer": Persona(
        id="newcomer",
        label="Newcomer",
        description="New to football: the story in plain words plus a one-line explanation of the key term.",
        include_stats=False,
        include_gloss=True,
        default_register="simple",
        keeps=("story", "scoreline", "names", "term_glosses"),
        omits=("counts", "time_windows", "zones"),
    ),
}


def get_persona(persona_id: str) -> Persona:
    try:
        return PERSONAS[persona_id]
    except KeyError:
        raise ValueError(
            f"unknown persona {persona_id!r}; expected one of {sorted(PERSONAS)}"
        ) from None

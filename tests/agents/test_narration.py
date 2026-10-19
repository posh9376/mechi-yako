import re

import pytest

from agents.language_qa import check_narrative
from agents.narrator.sw import narrate_sw
from agents.persona.writer import write_en
from api.data import get_moments
from tests.conftest import MATCH_ID

PERSONAS = ("analyst", "casual", "newcomer")
WRITERS = {"en": write_en, "sw": narrate_sw}


def _all_moments():
    for source in ("fixture", "live"):
        for moment in get_moments(MATCH_ID, source):
            yield pytest.param(moment, id=f"{source}:{moment['id']}")


@pytest.mark.parametrize("moment", list(_all_moments()))
@pytest.mark.parametrize("persona", PERSONAS)
@pytest.mark.parametrize("language", ("en", "sw"))
@pytest.mark.parametrize("register", (None, "formal", "casual", "simple"))
def test_every_narrative_passes_qa(match_doc, moment, persona, language, register):
    narrative = WRITERS[language](moment, match_doc["match"], persona, register)
    qa = check_narrative(narrative, moment)
    assert qa["status"] == "pass", (qa["reasons"], narrative["text"])
    assert set(narrative["event_ids"]) <= set(moment["event_ids"])


def _equaliser(fixture_doc):
    return next(m for m in fixture_doc["moments"] if m["id"] == "mom-goal-equaliser-01")


def test_equaliser_facts_do_not_drift_across_personas_and_languages(match_doc, fixture_doc):
    moment = _equaliser(fixture_doc)
    for language, write in WRITERS.items():
        for persona in PERSONAS:
            narrative = write(moment, match_doc["match"], persona)
            text = narrative["text"]
            assert "Omar Diallo" in text, (language, persona, text)
            assert "1–1" in text or "Blue Herons 1, Red Kites 1" in text, (language, persona, text)
            assert narrative["stats_used"]["score_after"] == [1, 1]
            assert narrative["entities_used"]["scorer"] == "RK-9"


def test_kiswahili_formal_equaliser_line(match_doc, fixture_doc):
    narrative = narrate_sw(_equaliser(fixture_doc), match_doc["match"], "analyst", "formal")
    assert narrative["register"] == "formal"
    assert narrative["text"].startswith("Dakika ya 63, Omar Diallo anafunga bao la kusawazisha")
    assert check_narrative(narrative, _equaliser(fixture_doc))["status"] == "pass"


def test_analyst_has_counts_casual_does_not(match_doc, fixture_doc):
    press = next(m for m in fixture_doc["moments"] if m["type"] == "pressure_spell")
    analyst = write_en(press, match_doc["match"], "analyst")
    casual = write_en(press, match_doc["match"], "casual")
    assert "high_turnovers" in analyst["stats_used"]
    assert str(press["stats"]["high_turnovers"]) in analyst["text"]
    assert not re.search(r"\d", casual["text"])
    assert casual["stats_used"] == {}


def test_newcomer_gets_a_gloss(match_doc, fixture_doc):
    press = next(m for m in fixture_doc["moments"] if m["type"] == "pressure_spell")
    assert "Pressing means" in write_en(press, match_doc["match"], "newcomer")["text"]
    assert "Kubana ni pale" in narrate_sw(press, match_doc["match"], "newcomer")["text"]


@pytest.mark.parametrize("language", ("en", "sw"))
def test_persona_default_registers(match_doc, fixture_doc, language):
    goal = _equaliser(fixture_doc)
    write = WRITERS[language]
    assert write(goal, match_doc["match"], "analyst")["register"] == "formal"
    assert write(goal, match_doc["match"], "casual")["register"] == "casual"
    assert write(goal, match_doc["match"], "newcomer")["register"] == "simple"


def test_kiswahili_casual_sample_matches_lexicon(match_doc, fixture_doc):
    from lexicon import load_lexicon

    sample = load_lexicon().registers["casual"]["samples"][0]["text"]
    assert narrate_sw(_equaliser(fixture_doc), match_doc["match"], "casual")["text"] == sample

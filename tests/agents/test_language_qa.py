from agents.language_qa import check_narrative
from agents.narrator.sw import narrate_sw
from agents.persona.writer import write_en


def _press(fixture_doc):
    return next(m for m in fixture_doc["moments"] if m["type"] == "pressure_spell")


def _goal(fixture_doc):
    return next(m for m in fixture_doc["moments"] if m["id"] == "mom-goal-equaliser-01")


def test_wrong_number_in_text_is_flagged(match_doc, fixture_doc):
    moment = _goal(fixture_doc)
    narrative = write_en(moment, match_doc["match"], "analyst")
    narrative["text"] = narrative["text"].replace("1–1", "2–1")
    qa = check_narrative(narrative, moment)
    assert qa["status"] == "flag"
    assert any("numbers not backed" in r for r in qa["reasons"])


def test_wrong_number_word_in_kiswahili_is_flagged(match_doc, fixture_doc):
    moment = _press(fixture_doc)
    narrative = narrate_sw(moment, match_doc["match"], "analyst")
    assert "mara tano" in narrative["text"]
    narrative["text"] = narrative["text"].replace("mara tano", "mara nane", 1)
    qa = check_narrative(narrative, moment)
    assert qa["status"] == "flag"
    assert any("[8]" in r for r in qa["reasons"])


def test_stats_used_must_match_fact_layer(match_doc, fixture_doc):
    moment = _press(fixture_doc)
    narrative = write_en(moment, match_doc["match"], "analyst")
    narrative["stats_used"]["high_turnovers"] = 9
    qa = check_narrative(narrative, moment)
    assert qa["status"] == "flag"
    assert any("high_turnovers" in r for r in qa["reasons"])


def test_foreign_event_ids_are_flagged(match_doc, fixture_doc):
    moment = _goal(fixture_doc)
    narrative = write_en(moment, match_doc["match"], "casual")
    narrative["event_ids"] = ["e-0001"]
    assert check_narrative(narrative, moment)["status"] == "flag"


def test_missing_required_term_is_flagged(match_doc, fixture_doc):
    moment = _press(fixture_doc)
    narrative = narrate_sw(moment, match_doc["match"], "casual")
    narrative["text"] = "Red Kites wako vizuri sana leo."
    qa = check_narrative(narrative, moment)
    assert qa["status"] == "flag"
    assert any("missing required sw terms" in r for r in qa["reasons"])


def test_english_leaking_into_kiswahili_is_flagged(match_doc, fixture_doc):
    moment = _goal(fixture_doc)
    narrative = narrate_sw(moment, match_doc["match"], "casual")
    narrative["text"] += " The goal was great."
    qa = check_narrative(narrative, moment)
    assert qa["status"] == "flag"
    assert any("English words" in r for r in qa["reasons"])


def test_unknown_entity_is_flagged(match_doc, fixture_doc):
    moment = _goal(fixture_doc)
    narrative = write_en(moment, match_doc["match"], "casual")
    narrative["entities_used"]["scorer"] = "BH-9"
    assert check_narrative(narrative, moment)["status"] == "flag"

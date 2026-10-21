from agents.persona import PERSONAS
from lexicon import load_lexicon
from tests.conftest import MOMENT_TYPES


def test_lexicon_size_and_moment_coverage():
    lex = load_lexicon()
    assert 40 <= len(lex.terms) <= 60
    assert set(lex.moment_terms) == MOMENT_TYPES


def test_lexicon_is_approved_by_native_reviewers():
    lex = load_lexicon()
    assert lex.review_status == "approved"
    assert all(t.review == "approved" for t in lex.terms.values())


def test_formal_samples_use_required_terms():
    lex = load_lexicon()
    samples = lex.registers["formal"]["samples"]
    assert 3 <= len(samples) <= 5
    for sample in samples:
        found = lex.find_terms(sample["text"], "sw")
        required = set(lex.required_terms(sample["moment_type"]))
        assert required <= found, (sample["moment_type"], required - found)


def test_personas_cover_three_viewers():
    assert set(PERSONAS) == {"analyst", "casual", "newcomer"}
    assert PERSONAS["analyst"].include_stats
    assert not PERSONAS["casual"].include_stats
    assert PERSONAS["newcomer"].include_gloss

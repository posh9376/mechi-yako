import copy
import json

from api.data import FIXTURES_DIR, MATCHES_DIR
from generator.realism import report_passed, run_realism_report
from generator.scripted_demo import MATCH_ID, build_demo_match, build_demo_match_public


def test_public_demo_match_passes_realism():
    results = run_realism_report(build_demo_match_public())
    assert report_passed(results), [r for r in results if not r.passed]


def test_public_match_strips_planted_hints():
    assert "_planted" in build_demo_match()
    assert "_planted" not in build_demo_match_public()


def test_committed_match_matches_builder():
    committed = json.loads((MATCHES_DIR / f"{MATCH_ID}.json").read_text(encoding="utf-8"))
    assert committed == build_demo_match_public()


def test_committed_fixture_exists_with_five_moments():
    fixture = json.loads((FIXTURES_DIR / f"{MATCH_ID}.moments.json").read_text(encoding="utf-8"))
    assert len(fixture["moments"]) == 5


def test_realism_catches_score_mismatch():
    doc = copy.deepcopy(build_demo_match_public())
    doc["match"]["score_ft"] = [3, 0]
    results = {r.name: r for r in run_realism_report(doc)}
    assert not results["score_matches_goals"].passed

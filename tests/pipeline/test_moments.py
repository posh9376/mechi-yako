from pipeline.moments import MomentDetector
from pipeline.replay import MatchReplay
from tests.conftest import MOMENT_TYPES


def _detect(match_doc):
    return MomentDetector(match_doc["match"]).detect_all(match_doc["events"])


def _by_type(moments, moment_type):
    return [m for m in moments if m["type"] == moment_type]


def test_all_five_types_detected(match_doc):
    assert {m["type"] for m in _detect(match_doc)} == MOMENT_TYPES


def test_pressure_spell_is_red_kites_in_blue_herons_half(match_doc):
    (press,) = _by_type(_detect(match_doc), "pressure_spell")
    assert press["team"] == "RK"
    assert press["stats"]["zone"] == "BH_own_half"
    assert press["stats"]["high_turnovers"] >= 3
    assert press["stats"]["pressure_events"] >= 3
    assert press["entities"]["key_player"] == "RK-4"


def test_equaliser_scored_by_rk9(match_doc):
    goals = _by_type(_detect(match_doc), "goal")
    equaliser = next(g for g in goals if g["team"] == "RK")
    assert equaliser["stats"]["scorer"] == "RK-9"
    assert equaliser["stats"]["score_after"] == [1, 1]
    assert equaliser["stats"]["minute"] == 63


def test_momentum_swing_goes_from_trailing_to_level(match_doc):
    (swing,) = _by_type(_detect(match_doc), "momentum_swing")
    assert swing["team"] == "RK"
    assert swing["stats"]["score_before"] == [1, 0]
    assert swing["stats"]["score_after"] == [1, 1]


def test_rk4_milestone(match_doc):
    (milestone,) = _by_type(_detect(match_doc), "player_milestone")
    assert milestone["stats"]["player"] == "RK-4"
    assert milestone["stats"]["value"] == 5
    assert milestone["t_peak"] == "78:14"


def test_every_moment_cites_real_events(match_doc):
    ids = {e["id"] for e in match_doc["events"]}
    for moment in _detect(match_doc):
        assert moment["event_ids"], moment["id"]
        assert set(moment["event_ids"]) <= ids, moment["id"]


def test_detect_all_is_repeatable(match_doc):
    detector = MomentDetector(match_doc["match"])
    first = detector.detect_all(match_doc["events"])
    second = detector.detect_all(match_doc["events"])
    assert first == second


def test_online_ingest_finds_goals_and_milestone(match_doc):
    detector = MomentDetector(match_doc["match"])
    seen = []
    for event in MatchReplay(match_doc, instant=True).iter_events():
        seen.extend(detector.ingest(event))
    types = {m["type"] for m in seen}
    assert {"goal", "momentum_swing", "player_milestone", "shot_after_turnovers"} <= types

from pipeline.replay import MatchReplay
from pipeline.state import MatchStateAggregator


def _final_state(match_doc):
    agg = MatchStateAggregator(match_doc["match"])
    agg.ingest_all(match_doc["events"])
    return agg.state


def test_full_time_score_and_goals(match_doc):
    state = _final_state(match_doc)
    assert state.score == [1, 1]
    assert state.teams["BH"].goals == 1
    assert state.teams["RK"].goals == 1
    assert state.events_seen == len(match_doc["events"]) == 123


def test_rk4_tackle_count(match_doc):
    state = _final_state(match_doc)
    assert state.player_tackles_won["RK-4"] == 5
    assert state.teams["RK"].tackles_won >= 5


def test_half_time_score(match_doc):
    events = MatchReplay(match_doc, instant=True, end_clock="45:00").events
    agg = MatchStateAggregator(match_doc["match"])
    agg.ingest_all(events)
    assert agg.state.score == match_doc["match"]["score_ht"] == [1, 0]


def test_snapshot_shape(match_doc):
    agg = MatchStateAggregator(match_doc["match"])
    agg.ingest_all(match_doc["events"])
    snap = agg.snapshot()
    assert set(snap["possession"]) == {"BH", "RK"}
    assert abs(sum(snap["possession"].values()) - 1.0) < 0.01
    for team in snap["teams"].values():
        if team["pass_completion"] is not None:
            assert 0 <= team["pass_completion"] <= 1


def test_rolling_window_is_trimmed(match_doc):
    agg = MatchStateAggregator(match_doc["match"], window_seconds=300)
    agg.ingest_all(match_doc["events"])
    clocks = [item[0] for item in agg.state.recent]
    assert clocks and max(clocks) - min(clocks) <= 300

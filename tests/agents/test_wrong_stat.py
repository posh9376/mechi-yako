"""Injected wrong-stat test: an unreproducible claim must be blocked and audited."""

from tests.conftest import MATCH_ID


def _check(client, **body):
    res = client.post(f"/matches/{MATCH_ID}/claims/check", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_injected_wrong_turnover_count_is_blocked_and_audited(client):
    decision = _check(
        client, moment_id="mom-pressure-01", source="fixture", metric="high_turnovers", value=99
    )
    assert decision["status"] == "blocked"
    assert decision["recomputed"] == 5
    assert decision["claimed"] == 99

    audit = client.get(f"/matches/{MATCH_ID}/audit").json()
    assert audit["count"] == 1
    entry = audit["entries"][0]
    assert entry["moment_id"] == "mom-pressure-01"
    assert entry["metric"] == "high_turnovers"
    assert entry["status"] == "blocked"
    assert entry["origin"] == "claims/check"


def test_true_claim_is_approved_and_audited(client):
    decision = _check(
        client, moment_id="mom-goal-equaliser-01", source="fixture", metric="score_after", value=[1, 1]
    )
    assert decision["status"] == "approved"
    assert client.get(f"/matches/{MATCH_ID}/audit").json()["count"] == 1


def test_wrong_scorer_is_blocked(client):
    decision = _check(
        client, moment_id="mom-goal-equaliser-01", source="fixture", metric="scorer", value="BH-9"
    )
    assert decision["status"] == "blocked"
    assert decision["recomputed"] == "RK-9"


def test_citing_nonexistent_events_is_blocked(client):
    decision = _check(
        client,
        moment_id="mom-goal-equaliser-01",
        source="fixture",
        metric="score_after",
        value=[1, 1],
        event_ids=["e-9999"],
    )
    assert decision["status"] == "blocked"
    assert "do not exist" in decision["reason"]


def test_unknown_metric_is_blocked(client):
    decision = _check(
        client, moment_id="mom-goal-equaliser-01", source="fixture", metric="vibes", value=10
    )
    assert decision["status"] == "blocked"
    assert decision["metric_in_fact_layer"] is False


def test_rounded_window_is_corrected(client):
    decision = _check(
        client, moment_id="mom-pressure-01", source="fixture", metric="window_minutes", value=7
    )
    assert decision["status"] == "corrected"
    assert decision["corrected_value"] == 6.7

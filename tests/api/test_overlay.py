from tests.conftest import MATCH_ID


def test_overlay_equaliser_is_timed_json(client):
    res = client.get(
        f"/matches/{MATCH_ID}/moments/mom-goal-equaliser-01/overlay",
        params={"source": "fixture"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["schema"] == "mechi-yako-overlay-v1"
    assert body["moment_id"] == "mom-goal-equaliser-01"
    assert body["moment_type"] == "goal"
    assert body["t"] == "63:02"
    assert body["score"] == {"home": 1, "away": 1}
    assert body["team"] == "RK"
    assert body["event_ids"] == ["e-0100"]
    assert "equalised" in body["text"].lower()
    assert [step["role"] for step in body["pipeline"]] == [
        "Ingest",
        "Interpret",
        "Explain",
        "Verify",
        "Render",
        "Personalize",
    ]


def test_overlay_live_goal_matches_state(client):
    moments = client.get(f"/matches/{MATCH_ID}/moments").json()["moments"]
    goal = next(m for m in moments if m["type"] == "goal" and m["t_peak"] >= "60:00")
    body = client.get(f"/matches/{MATCH_ID}/moments/{goal['id']}/overlay").json()
    state = client.get(f"/matches/{MATCH_ID}/state", params={"at": goal["t_peak"]}).json()["state"]
    assert body["score"] == {"home": state["score"][0], "away": state["score"][1]}
    assert body["event_ids"] == goal["event_ids"]


def test_overlay_unknown_moment_is_404(client):
    res = client.get(f"/matches/{MATCH_ID}/moments/no-such-moment/overlay")
    assert res.status_code == 404

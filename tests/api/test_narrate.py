from tests.conftest import MATCH_ID


def _narrate(client, **body):
    return client.post(f"/matches/{MATCH_ID}/narrate", json=body)


def test_narrate_fixture_equaliser_in_kiswahili(client):
    res = _narrate(
        client, moment_id="mom-goal-equaliser-01", source="fixture", persona="analyst", language="sw"
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["qa"]["status"] == "pass"
    assert body["narrative"]["language"] == "sw"
    assert body["narrative"]["register"] == "formal"
    assert "Omar Diallo" in body["narrative"]["text"]
    assert body["verification"]["blocked"] == []


def test_narrate_live_moment(client):
    moments = client.get(f"/matches/{MATCH_ID}/moments").json()["moments"]
    milestone = next(m for m in moments if m["type"] == "player_milestone")
    res = _narrate(client, moment_id=milestone["id"], persona="newcomer", language="en")
    assert res.status_code == 200
    body = res.json()
    assert body["qa"]["status"] == "pass"
    assert "Makena Aoko" in body["narrative"]["text"]


def test_narrate_applies_verifier_corrections(client):
    res = _narrate(
        client, moment_id="mom-pressure-01", source="fixture", persona="analyst", language="en"
    )
    body = res.json()
    assert body["qa"]["status"] == "pass"
    assert "6.7 minutes" in body["narrative"]["text"]
    assert body["verification"]["corrected"][0]["metric"] == "window_minutes"


def test_narrate_validation(client):
    assert _narrate(client, moment_id="mom-nope", persona="analyst", language="en").status_code == 404
    assert (
        _narrate(client, moment_id="mom-goal-01", persona="pundit", language="en").status_code == 422
    )
    assert (
        _narrate(client, moment_id="mom-goal-01", persona="analyst", language="fr").status_code == 422
    )


def test_claims_endpoint_summary(client):
    body = client.get(f"/matches/{MATCH_ID}/claims", params={"source": "fixture"}).json()
    assert body["summary"]["blocked"] == 0
    assert body["summary"]["corrected"] == 1
    assert body["summary"]["approved"] > 10
    # Reading claims does not write to the audit log.
    assert client.get(f"/matches/{MATCH_ID}/audit").json()["count"] == 0


def test_personas_options(client):
    body = client.get("/personas").json()
    assert {p["id"] for p in body["personas"]} == {"analyst", "casual", "newcomer"}
    assert body["languages"] == ["en", "sw"]
    assert "formal" in body["registers"]["sw"]
    assert body["lexicon"]["review"] == "pending"

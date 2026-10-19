from tests.conftest import MATCH_ID, MOMENT_TYPES


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["match_id"] == MATCH_ID
    assert body["fixture_moments"] == 5


def test_match_metadata(client):
    res = client.get(f"/matches/{MATCH_ID}")
    assert res.status_code == 200
    body = res.json()
    assert body["schema_version"] == "1.0"
    assert body["match"]["home"]["code"] == "BH"
    assert body["match"]["away"]["code"] == "RK"
    assert body["match"]["score_ft"] == [1, 1]
    assert body["event_count"] == 123


def test_fixture_moments_cover_all_types(client):
    res = client.get(f"/matches/{MATCH_ID}/moments", params={"source": "fixture"})
    assert res.status_code == 200
    body = res.json()
    assert body["schema_version"] == "1.0"
    assert body["source"] == "fixture"
    assert {m["type"] for m in body["moments"]} == MOMENT_TYPES
    for moment in body["moments"]:
        assert moment["event_ids"], moment["id"]
        assert moment["match_id"] == MATCH_ID


def test_unknown_match_is_404(client):
    assert client.get("/matches/m-nope").status_code == 404
    assert client.get("/matches/..%2Fsecrets").status_code == 404


def test_bad_source_is_422(client):
    res = client.get(f"/matches/{MATCH_ID}/moments", params={"source": "made-up"})
    assert res.status_code == 422

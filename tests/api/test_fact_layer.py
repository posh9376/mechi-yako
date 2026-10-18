import json

from tests.conftest import MATCH_ID, MOMENT_TYPES


def test_live_moments_are_default(client):
    res = client.get(f"/matches/{MATCH_ID}/moments")
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "live"
    assert {m["type"] for m in body["moments"]} == MOMENT_TYPES


def test_state_full_time(client):
    body = client.get(f"/matches/{MATCH_ID}/state").json()
    assert body["state"]["score"] == [1, 1]
    assert body["state"]["events_seen"] == 123
    assert body["state"]["player_tackles_won"]["RK-4"] == 5


def test_state_at_clock(client):
    assert client.get(f"/matches/{MATCH_ID}/state", params={"at": "45:00"}).json()["state"]["score"] == [1, 0]
    assert client.get(f"/matches/{MATCH_ID}/state", params={"at": "63:01"}).json()["state"]["score"] == [1, 0]
    assert client.get(f"/matches/{MATCH_ID}/state", params={"at": "63:02"}).json()["state"]["score"] == [1, 1]


def test_event_window(client):
    body = client.get(f"/matches/{MATCH_ID}/events", params={"start": "55:00", "end": "65:00"}).json()
    events = body["events"]
    assert events
    for e in events:
        minutes, seconds = map(int, e["t"].split(":"))
        assert 55 * 60 <= minutes * 60 + seconds <= 65 * 60
    assert any(e["type"] == "shot" and e["outcome"] == "goal" for e in events)


def test_all_events_in_clock_order(client):
    events = client.get(f"/matches/{MATCH_ID}/events").json()["events"]
    assert len(events) == 123
    clocks = [tuple(map(int, e["t"].split(":"))) for e in events]
    assert clocks == sorted(clocks)


def test_bad_clock_is_422(client):
    assert client.get(f"/matches/{MATCH_ID}/events", params={"start": "soon"}).status_code == 422
    assert client.get(f"/matches/{MATCH_ID}/state", params={"at": "1:2:3"}).status_code == 422


def _read_sse(response):
    frames = []
    event_name = None
    for line in response.iter_lines():
        if line.startswith("event: "):
            event_name = line[len("event: "):]
        elif line.startswith("data: "):
            frames.append((event_name, json.loads(line[len("data: "):])))
    return frames


def test_feed_streams_events_moments_and_done(client):
    with client.stream(
        "GET", f"/matches/{MATCH_ID}/feed", params={"instant": "true", "start": "55:00", "end": "65:00"}
    ) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        frames = _read_sse(res)

    names = [name for name, _ in frames]
    assert names[-1] == "done"
    match_events = [payload for name, payload in frames if name == "match_event"]
    moments = [payload for name, payload in frames if name == "moment"]
    done = frames[-1][1]
    assert done["events"] == len(match_events) > 0
    assert done["moments"] == len(moments)
    assert {"goal", "momentum_swing"} <= {m["type"] for m in moments}
    assert match_events[0]["score"] == [1, 0]
    assert match_events[-1]["score"] == [1, 1]
    assert all(m["t_peak"] >= "55:00" for m in moments)


def test_feed_full_match_ends_level(client):
    with client.stream("GET", f"/matches/{MATCH_ID}/feed", params={"instant": "true"}) as res:
        frames = _read_sse(res)
    assert frames[-1][0] == "done"
    assert frames[-1][1]["score"] == [1, 1]
    assert frames[-1][1]["events"] == 123

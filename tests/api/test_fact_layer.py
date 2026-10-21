import asyncio
import json
import threading
import time

from api.feed import stream_match, until_disconnect
from pipeline.clock import parse_clock
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
    assert names[0] == "snapshot"
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


def test_feed_snapshot_is_empty_from_kickoff(client):
    with client.stream("GET", f"/matches/{MATCH_ID}/feed", params={"instant": "true"}) as res:
        name, snapshot = _read_sse(res)[0]
    assert name == "snapshot"
    assert snapshot == {"clock": "0:00", "score": [0, 0], "events": [], "moments": []}


def test_feed_snapshot_carries_history_when_joining_mid_match(client):
    with client.stream(
        "GET", f"/matches/{MATCH_ID}/feed", params={"instant": "true", "start": "55:00"}
    ) as res:
        frames = _read_sse(res)

    name, snapshot = frames[0]
    assert name == "snapshot"
    assert snapshot["clock"] == "55:00"
    assert snapshot["score"] == [1, 0]
    assert all(parse_clock(e["t"]) < 55 * 60 for e in snapshot["events"])
    assert len(snapshot["events"]) + frames[-1][1]["events"] == 123
    assert any(m["type"] == "goal" and parse_clock(m["t_peak"]) < 55 * 60 for m in snapshot["moments"])

    streamed = [payload["id"] for name, payload in frames if name == "moment"]
    past = [m["id"] for m in snapshot["moments"]]
    live = [m["id"] for m in client.get(f"/matches/{MATCH_ID}/moments").json()["moments"]]
    assert not set(past) & set(streamed)
    assert sorted(past + streamed) == sorted(live)


def test_feed_moments_match_live_moments(client):
    with client.stream("GET", f"/matches/{MATCH_ID}/feed", params={"instant": "true"}) as res:
        streamed = [payload for name, payload in _read_sse(res) if name == "moment"]
    live = client.get(f"/matches/{MATCH_ID}/moments").json()["moments"]
    assert streamed == live


def _replay_threads():
    return [t for t in threading.enumerate() if t.name == "feed-replay"]


def _wait_for_replay_threads(count: int) -> int:
    deadline = time.monotonic() + 2
    while len(_replay_threads()) > count and time.monotonic() < deadline:
        time.sleep(0.02)
    return len(_replay_threads())


def test_feed_server_closes_stream_when_client_leaves(match_doc):
    before = len(_replay_threads())

    async def read_two_then_leave():
        stream = until_disconnect(
            stream_match(match_doc, speed=1, instant=False, start_clock="55:00", end_clock=None)
        )
        names = [(await stream.__anext__()).split("\n", 1)[0] for _ in range(2)]
        await stream.aclose()
        return names

    assert asyncio.run(read_two_then_leave()) == ["event: snapshot", "event: match_event"]
    assert _wait_for_replay_threads(before) == before


def test_feed_replay_thread_stops_when_generator_closes(match_doc):
    before = len(_replay_threads())
    frames = stream_match(match_doc, speed=1, instant=False, start_clock="55:00", end_clock=None)
    assert next(frames).startswith("event: snapshot")
    assert next(frames).startswith("event: match_event")
    assert len(_replay_threads()) == before + 1

    frames.close()
    assert _wait_for_replay_threads(before) == before

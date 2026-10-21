"""Server-sent events feed: replay a match onto an in-process queue and stream it."""

from __future__ import annotations

import json
import threading
from typing import Any, AsyncIterator, Iterator

from starlette.concurrency import iterate_in_threadpool

from pipeline.clock import format_clock, parse_clock
from pipeline.moments import MomentDetector
from pipeline.queue import InProcessEventQueue
from pipeline.replay import MatchReplay


async def until_disconnect(frames: Iterator[str]) -> AsyncIterator[str]:
    """Serve ``frames`` from a worker thread and close them once the client goes away.

    Starlette drops a sync iterator without closing it, which would leave the replay
    thread publishing to nobody until the match ends.
    """
    try:
        async for frame in iterate_in_threadpool(frames):
            yield frame
    finally:
        frames.close()


def _frame(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def stream_match(
    doc: dict[str, Any],
    *,
    speed: float,
    instant: bool,
    start_clock: str | None,
    end_clock: str | None,
) -> Iterator[str]:
    """Yield SSE frames: a ``snapshot`` of what happened before ``start_clock``, one
    ``match_event`` per event, ``moment`` frames as the online detector fires, then ``done``.

    Each connection gets its own queue and replay thread, mirroring
    ``python -m pipeline.replay --via-queue``. The replay thread stops as soon as the
    client goes away, so pausing or seeking does not leave sleepers behind.
    """
    replay = MatchReplay(
        doc, speed=speed, instant=instant, start_clock=start_clock, end_clock=end_clock
    )
    detector = MomentDetector(doc["match"])
    start_s = parse_clock(start_clock) if start_clock is not None else 0
    past_events: list[dict[str, Any]] = []
    past_moments: list[dict[str, Any]] = []
    if start_clock is not None:
        for event in MatchReplay(doc, instant=True).events:
            if parse_clock(event["t"]) >= start_s:
                break
            past_moments.extend(detector.ingest(event))
            past_events.append(event)

    queue = InProcessEventQueue()
    stop = threading.Event()

    def produce() -> None:
        try:
            for event in replay.iter_events(sleep=stop.wait):
                if stop.is_set():
                    break
                queue.publish(event)
        finally:
            queue.close()

    yield _frame(
        "snapshot",
        {
            "clock": format_clock(start_s),
            "score": list(detector.agg.state.score),
            "events": past_events,
            "moments": past_moments,
        },
    )

    producer = threading.Thread(target=produce, name="feed-replay", daemon=True)
    producer.start()
    count = 0
    moments = 0
    try:
        for event in queue:
            new_moments = detector.ingest(event)
            count += 1
            yield _frame(
                "match_event",
                {
                    "event": event,
                    "clock": event["t"],
                    "score": list(detector.agg.state.score),
                },
            )
            for moment in new_moments:
                moments += 1
                yield _frame("moment", moment)

        yield _frame("done", {"events": count, "moments": moments, "score": list(detector.agg.state.score)})
    finally:
        stop.set()

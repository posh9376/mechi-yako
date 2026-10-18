"""Server-sent events feed: replay a match onto an in-process queue and stream it."""

from __future__ import annotations

import json
import threading
from typing import Any, Iterator

from pipeline.clock import parse_clock
from pipeline.moments import MomentDetector
from pipeline.queue import InProcessEventQueue
from pipeline.replay import MatchReplay


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
    """Yield SSE frames: one ``match_event`` per event, ``moment`` frames as the
    online detector fires, then a final ``done`` frame.

    Each connection gets its own queue and replay thread, mirroring
    ``python -m pipeline.replay --via-queue``. Events before ``start_clock`` are
    folded into the detector silently so score and windows are correct mid-match.
    """
    replay = MatchReplay(
        doc, speed=speed, instant=instant, start_clock=start_clock, end_clock=end_clock
    )
    detector = MomentDetector(doc["match"])
    if start_clock is not None:
        start_s = parse_clock(start_clock)
        for event in MatchReplay(doc, instant=True).events:
            if parse_clock(event["t"]) >= start_s:
                break
            detector.ingest(event)
    queue = InProcessEventQueue()
    producer = threading.Thread(target=replay.play, args=(queue,), daemon=True)
    producer.start()

    count = 0
    moments = 0
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

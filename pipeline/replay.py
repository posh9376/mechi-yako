"""Replay a stored match document as a timed event stream."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from pipeline.clock import parse_clock
from pipeline.queue import EventSink, InProcessEventQueue

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATCH = ROOT / "data" / "matches" / "m-demo-001.json"

__all__ = ["MatchReplay", "load_match", "parse_clock"]


def load_match(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if "events" not in doc or "match" not in doc:
        raise ValueError(f"{path} is not a schema v1 match document")
    return doc


class MatchReplay:
    """Stream match events in clock order.

    Parameters
    ----------
    speed:
        Match-seconds per wall-clock second. ``1.0`` is real time,
        ``60.0`` plays one match-minute per wall second, ``0`` (or ``instant=True``)
        emits as fast as possible with no sleeps.
    start_clock / end_clock:
        Optional inclusive window as match-clock strings (e.g. ``\"55:00\"``).
    """

    def __init__(
        self,
        doc: dict[str, Any],
        *,
        speed: float = 60.0,
        instant: bool = False,
        start_clock: str | None = None,
        end_clock: str | None = None,
    ) -> None:
        self.doc = doc
        self.speed = float(speed)
        self.instant = instant or self.speed <= 0
        self.start_s = parse_clock(start_clock) if start_clock else None
        self.end_s = parse_clock(end_clock) if end_clock else None
        self._events = self._select_events(doc["events"])

    @classmethod
    def from_path(cls, path: str | Path, **kwargs: Any) -> MatchReplay:
        return cls(load_match(path), **kwargs)

    def _select_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered = sorted(events, key=lambda e: (parse_clock(e["t"]), e["id"]))
        out: list[dict[str, Any]] = []
        for e in ordered:
            s = parse_clock(e["t"])
            if self.start_s is not None and s < self.start_s:
                continue
            if self.end_s is not None and s > self.end_s:
                continue
            out.append(e)
        return out

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def iter_events(
        self,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> Iterable[dict[str, Any]]:
        """Yield events, sleeping between clock gaps according to ``speed``."""
        prev_s: int | None = None
        for event in self._events:
            s = parse_clock(event["t"])
            if not self.instant and prev_s is not None and s > prev_s:
                gap = (s - prev_s) / self.speed
                if gap > 0:
                    sleep(gap)
            prev_s = s
            yield event

    def play(
        self,
        sink: EventSink,
        *,
        sleep: Callable[[float], None] = time.sleep,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> int:
        """Publish all selected events to ``sink``. Returns count published."""
        n = 0
        try:
            for event in self.iter_events(sleep=sleep):
                sink.publish(event)
                if on_event:
                    on_event(event)
                n += 1
        finally:
            sink.close()
        return n


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Replay a synthetic match onto an in-process queue")
    parser.add_argument(
        "--match",
        type=Path,
        default=DEFAULT_MATCH,
        help="Path to match JSON (default: data/matches/m-demo-001.json)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=120.0,
        help="Match-seconds per wall second (default 120 ≈ 45s for a full match)",
    )
    parser.add_argument(
        "--instant",
        action="store_true",
        help="Emit all events with no delays (for smoke tests)",
    )
    parser.add_argument("--start", type=str, default=None, help="Start clock, e.g. 55:00")
    parser.add_argument("--end", type=str, default=None, help="End clock, e.g. 65:00")
    parser.add_argument(
        "--print-every",
        type=int,
        default=1,
        help="Print every Nth event (default 1; use 0 to silence)",
    )
    parser.add_argument(
        "--via-queue",
        action="store_true",
        help="Demonstrate publish→consume via InProcessEventQueue (same thread)",
    )
    args = parser.parse_args()

    replay = MatchReplay.from_path(
        args.match,
        speed=args.speed,
        instant=args.instant,
        start_clock=args.start,
        end_clock=args.end,
    )
    match_meta = replay.doc["match"]
    print(
        f"Replaying {match_meta['id']}: {match_meta['home']['name']} vs {match_meta['away']['name']} "
        f"({len(replay.events)} events, speed={args.speed}, instant={args.instant})"
    )

    def maybe_print(event: dict[str, Any], index: int) -> None:
        if args.print_every > 0 and index % args.print_every == 0:
            print(
                f"  [{event['t']:>5}] {event['type']:<14} {event['team']} "
                f"{event.get('player') or '-':<6} {event.get('outcome') or ''}"
            )

    if args.via_queue:
        # Collect into queue then drain — mirrors how an API worker would buffer.
        queue = InProcessEventQueue()
        n = 0

        def on_event(event: dict[str, Any]) -> None:
            nonlocal n
            n += 1
            maybe_print(event, n)

        count = replay.play(queue, on_event=on_event)
        leftover = queue.drain()
        print(f"Done. Published {count} events; queue leftover={len(leftover)}.")
        return 0

    n = 0
    for event in replay.iter_events():
        n += 1
        maybe_print(event, n)
    print(f"Done. Emitted {n} events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

"""Match pipeline libraries (Daniel) — replay, state, moments. HTTP lives in api/ (Posh)."""

from pipeline.queue import EventSink, InProcessEventQueue

__all__ = [
    "EventSink",
    "InProcessEventQueue",
    "MatchReplay",
    "load_match",
    "parse_clock",
]


def __getattr__(name: str):
    if name in {"MatchReplay", "load_match", "parse_clock"}:
        from pipeline import replay as _replay

        return getattr(_replay, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

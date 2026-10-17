"""Match pipeline libraries (Daniel) — replay, state, moments. HTTP lives in api/ (Posh)."""

from pipeline.queue import EventSink, InProcessEventQueue

__all__ = [
    "EventSink",
    "InProcessEventQueue",
    "MatchReplay",
    "MatchStateAggregator",
    "MomentDetector",
    "load_match",
    "parse_clock",
]


def __getattr__(name: str):
    if name in {"MatchReplay", "load_match", "parse_clock"}:
        from pipeline import replay as _replay

        return getattr(_replay, name)
    if name == "MatchStateAggregator":
        from pipeline.state import MatchStateAggregator

        return MatchStateAggregator
    if name == "MomentDetector":
        from pipeline.moments import MomentDetector

        return MomentDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

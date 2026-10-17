"""Shared match-clock helpers."""

from __future__ import annotations


def parse_clock(t: str) -> int:
    """Convert `M:SS` / `MM:SS` match clock to seconds from 0:00."""
    parts = t.split(":")
    if len(parts) != 2:
        raise ValueError(f"invalid clock {t!r}")
    return int(parts[0]) * 60 + int(parts[1])


def format_clock(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"

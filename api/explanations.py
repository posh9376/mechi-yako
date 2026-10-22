"""Explanation cache: one Foundry rewrite per moment, shared across requests.

The explainer package depends only on the moment, never on persona, language or
register, so it is computed once and reused. Concurrent requests for the same moment
wait on a single model call. Template fallbacks are never cached; after a failed call
Foundry is skipped for a short cooldown so a down endpoint is not hammered.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable

from agents.explainer import TemplateExplainer
from agents.foundry import FOUNDATION_NAME, TIMED_OUT, FoundryExplainer, explainer_status, make_explainer

CACHE_PATH_ENV = "MECHI_EXPLANATION_CACHE"
PREWARM_ENV = "MECHI_EXPLAINER_PREWARM"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[1] / ".cache" / "explanations.json"
FAILURE_COOLDOWN_S = 30.0
PREWARM_WORKERS = 3

log = logging.getLogger("uvicorn.error").getChild("explainer")


def _moment_hash(moment: dict[str, Any]) -> str:
    raw = json.dumps(moment, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _template_package(match_id: str, moment: dict[str, Any], error: str) -> dict[str, Any]:
    package = TemplateExplainer(match_id).explain_moment(moment)
    package["explainer"] = "template-v1"
    package["foundry_error"] = error
    return package


def cache_path_from_env() -> Path | None:
    value = os.environ.get(CACHE_PATH_ENV)
    if value is None:
        return DEFAULT_CACHE_PATH
    return Path(value) if value.strip() else None


class ExplanationCache:
    def __init__(self, path: Path | None = None, *, cooldown_s: float = FAILURE_COOLDOWN_S) -> None:
        self._path = path
        self._cooldown_s = cooldown_s
        self._lock = threading.Lock()
        self._save_lock = threading.Lock()
        self._done: dict[str, dict[str, Any]] = {}
        self._inflight: dict[str, Future[dict[str, Any]]] = {}
        self._cooldown_until = 0.0
        self._warm = {"total": 0, "done": 0, "running": False}
        self._load()

    def package(self, match_id: str, source: str, moment: dict[str, Any]) -> dict[str, Any]:
        """Explainer package for ``moment`` (claims not yet verified)."""
        if explainer_status()["active"] != FOUNDATION_NAME:
            return make_explainer(match_id).explain_moment(moment)

        key = "|".join(
            (match_id, source, moment["id"], FOUNDATION_NAME, FoundryExplainer.prompt_version, _moment_hash(moment))
        )
        with self._lock:
            cached = self._done.get(key)
            if cached is not None:
                return copy.deepcopy(cached)
            future = self._inflight.get(key)
            owner = future is None
            if owner:
                if time.monotonic() < self._cooldown_until:
                    return _template_package(
                        match_id, moment, "skipped: cooling down after a failed Foundry call"
                    )
                future = Future()
                self._inflight[key] = future

        if owner:
            started = time.perf_counter()
            try:
                package = FoundryExplainer(match_id).explain_moment(moment)
            except Exception as exc:  # noqa: BLE001 — waiters must always get a result
                package = _template_package(match_id, moment, str(exc)[:240])
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            ok = package.get("explainer") == FOUNDATION_NAME
            # A slow call is not an outage: only errors pause Foundry for other moments.
            timed_out = str(package.get("foundry_error", "")).startswith(TIMED_OUT)
            with self._lock:
                self._inflight.pop(key, None)
                if ok:
                    self._done[key] = copy.deepcopy(package)
                elif not timed_out:
                    self._cooldown_until = time.monotonic() + self._cooldown_s
            if ok:
                self._save()
                log.info("explained %s/%s via %s in %d ms", source, moment["id"], FOUNDATION_NAME, elapsed_ms)
            else:
                log.warning(
                    "Foundry failed for %s/%s after %d ms, using template: %s",
                    source, moment["id"], elapsed_ms, package.get("foundry_error"),
                )
            future.set_result(package)

        return copy.deepcopy(future.result())

    def warm(self, match_id: str, items: Iterable[tuple[str, dict[str, Any]]]) -> threading.Thread | None:
        """Explain ``(source, moment)`` pairs in the background, a few at a time."""
        if explainer_status()["active"] != FOUNDATION_NAME:
            return None
        work = list(items)
        with self._lock:
            self._warm = {"total": len(work), "done": 0, "running": True}

        def one(item: tuple[str, dict[str, Any]]) -> None:
            source, moment = item
            try:
                self.package(match_id, source, moment)
            finally:
                with self._lock:
                    self._warm["done"] += 1

        def run() -> None:
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=PREWARM_WORKERS, thread_name_prefix="explain-warm") as pool:
                list(pool.map(one, work))
            with self._lock:
                self._warm["running"] = False
            log.info("explanation pre-warm finished: %d moments in %.1f s", len(work), time.perf_counter() - started)

        thread = threading.Thread(target=run, name="explain-warm", daemon=True)
        thread.start()
        return thread

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"cached": len(self._done), "warm": dict(self._warm)}

    def _load(self) -> None:
        if self._path is None or not self._path.is_file():
            return
        try:
            entries = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(entries, dict):
            self._done.update({k: v for k, v in entries.items() if isinstance(v, dict)})

    def _save(self) -> None:
        if self._path is None:
            return
        with self._save_lock:
            with self._lock:
                snapshot = json.dumps(self._done, ensure_ascii=False, indent=1, sort_keys=True)
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._path.with_suffix(".tmp")
                tmp.write_text(snapshot, encoding="utf-8")
                tmp.replace(self._path)
            except OSError as exc:
                log.warning("could not write explanation cache %s: %s", self._path, exc)


def prewarm_enabled() -> bool:
    return (os.environ.get(PREWARM_ENV) or "1").strip().lower() not in {"0", "false", "no", "off"}

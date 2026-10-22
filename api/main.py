"""FastAPI app factory. Run locally with ``uvicorn api.main:app --reload``."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from dotenv import load_dotenv

from agents.foundry import explainer_status
from api import data
from api.claims import AgentsClaimChecker, AuditLog, Claim, claims_for_moment, verify_moment
from api.explanations import ExplanationCache, cache_path_from_env, prewarm_enabled
from api.feed import stream_match, until_disconnect
from api.narration import NarrationError, explain_moment, narrate, options
from pipeline.clock import parse_clock
from pipeline.replay import MatchReplay
from pipeline.state import MatchStateAggregator

load_dotenv()

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_MATCH_ID = "m-demo-001"


class NarrateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    moment_id: str
    persona: Literal["analyst", "casual", "newcomer"]
    language: Literal["en", "sw"]
    register_: Literal["formal", "casual", "simple"] | None = Field(None, alias="register")
    source: data.MomentSource = "live"
    explain: bool = Field(
        True,
        description="Include the explainer package for the Why? panel. False returns without waiting on it; "
        "fetch it from /matches/{id}/moments/{moment_id}/explain instead.",
    )


class ClaimCheckRequest(BaseModel):
    moment_id: str
    metric: str
    value: Any
    source: data.MomentSource = "live"
    event_ids: list[str] | None = Field(
        None, description="Override the moment's cited events (defaults to the moment's event_ids)"
    )


def _prewarm_items() -> list[tuple[str, dict[str, Any]]]:
    return [
        (source, moment)
        for source in ("live", "fixture")
        for moment in data.get_moments(DEFAULT_MATCH_ID, source)
    ]


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if prewarm_enabled():
            app.state.explanations.warm(DEFAULT_MATCH_ID, _prewarm_items())
        yield

    app = FastAPI(
        title="Mechi Yako API",
        version="0.1.0",
        description="Fact-layer API over the synthetic match pipeline.",
        lifespan=lifespan,
    )
    app.state.checker = AgentsClaimChecker()
    app.state.audit = AuditLog()
    app.state.explanations = ExplanationCache(cache_path_from_env())

    origins = [
        o.strip()
        for o in os.environ.get("MECHI_CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(data.MatchNotFound)
    async def _match_not_found(_: Request, exc: data.MatchNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": f"match {exc} not found"})

    @app.exception_handler(data.MomentNotFound)
    async def _moment_not_found(_: Request, exc: data.MomentNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": f"moment {exc} not found"})

    @app.get("/health")
    def health() -> dict:
        doc = data.get_match_doc(DEFAULT_MATCH_ID)
        fixture = data.get_fixture(DEFAULT_MATCH_ID)
        return {
            "status": "ok",
            "match_id": doc["match"]["id"],
            "schema_version": doc["schema_version"],
            "events": len(doc["events"]),
            "fixture_moments": len(fixture["moments"]),
            "live_moments": len(data.get_live_moments(DEFAULT_MATCH_ID)),
            "explainer": {**explainer_status(), **app.state.explanations.stats()},
        }

    @app.get("/matches")
    def list_matches() -> dict:
        return {"matches": data.available_matches()}

    @app.get("/matches/{match_id}")
    def get_match(match_id: str) -> dict:
        doc = data.get_match_doc(match_id)
        return {
            "schema_version": doc["schema_version"],
            "match": doc["match"],
            "event_count": len(doc["events"]),
        }

    @app.get("/matches/{match_id}/events")
    def get_events(
        match_id: str,
        start: str | None = Query(None, description="Inclusive start clock, e.g. 55:00"),
        end: str | None = Query(None, description="Inclusive end clock, e.g. 65:00"),
    ) -> dict:
        doc = data.get_match_doc(match_id)
        _validate_clock(start, "start")
        _validate_clock(end, "end")
        events = MatchReplay(doc, instant=True, start_clock=start, end_clock=end).events
        return {"match_id": match_id, "start": start, "end": end, "events": events}

    @app.get("/matches/{match_id}/state")
    def get_state(
        match_id: str,
        at: str | None = Query(None, description="Aggregate events up to and including this clock"),
    ) -> dict:
        doc = data.get_match_doc(match_id)
        _validate_clock(at, "at")
        events = MatchReplay(doc, instant=True, end_clock=at).events
        agg = MatchStateAggregator(doc["match"])
        agg.ingest_all(events)
        return {"match_id": match_id, "at": at, "state": agg.snapshot()}

    @app.get("/matches/{match_id}/moments")
    def get_moments(
        match_id: str,
        source: data.MomentSource = Query("live"),
    ) -> dict:
        moments = data.get_moments(match_id, source)
        return {
            "schema_version": "1.0",
            "match_id": match_id,
            "source": source,
            "moments": moments,
        }

    @app.get("/matches/{match_id}/feed")
    def get_feed(
        match_id: str,
        speed: float = Query(120.0, gt=0, le=6000, description="Match-seconds per wall second"),
        instant: bool = Query(False),
        start: str | None = Query(None),
        end: str | None = Query(None),
    ) -> StreamingResponse:
        doc = data.get_match_doc(match_id)
        _validate_clock(start, "start")
        _validate_clock(end, "end")
        frames = stream_match(doc, speed=speed, instant=instant, start_clock=start, end_clock=end)
        return StreamingResponse(
            until_disconnect(frames),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/personas")
    def get_options() -> dict:
        return options()

    @app.post("/matches/{match_id}/narrate")
    def post_narrate(match_id: str, body: NarrateRequest) -> dict:
        doc = data.get_match_doc(match_id)
        moment = data.get_moment(match_id, body.moment_id, body.source)
        try:
            return narrate(
                moment,
                doc,
                persona=body.persona,
                language=body.language,
                register=body.register_,
                checker=app.state.checker,
                explain=body.explain,
                source=body.source,
                cache=app.state.explanations,
            )
        except NarrationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    @app.get("/matches/{match_id}/moments/{moment_id}/explain")
    def get_explain(
        match_id: str,
        moment_id: str,
        source: data.MomentSource = Query("fixture"),
    ) -> dict:
        """Daniel's explainer + verifier for the Why? panel (no persona rewrite), cached per moment."""
        doc = data.get_match_doc(match_id)
        moment = data.get_moment(match_id, moment_id, source)
        return explain_moment(
            moment, doc, app.state.checker, source=source, cache=app.state.explanations
        )

    @app.get("/matches/{match_id}/claims")
    def get_claims(match_id: str, source: data.MomentSource = Query("live")) -> dict:
        doc = data.get_match_doc(match_id)
        claims = []
        for moment in data.get_moments(match_id, source):
            claims.extend(verify_moment(moment, doc, app.state.checker))
        summary = {
            status: sum(c["status"] == status for c in claims)
            for status in ("approved", "corrected", "blocked")
        }
        return {
            "match_id": match_id,
            "source": source,
            "checker": app.state.checker.name,
            "summary": summary,
            "claims": claims,
        }

    @app.post("/matches/{match_id}/claims/check")
    def post_claim_check(match_id: str, body: ClaimCheckRequest) -> dict:
        doc = data.get_match_doc(match_id)
        moment = data.get_moment(match_id, body.moment_id, body.source)
        known_metrics = {c.metric for c in claims_for_moment(moment)}
        event_ids = tuple(body.event_ids) if body.event_ids is not None else tuple(moment["event_ids"])
        claim = Claim(moment["id"], body.metric, body.value, event_ids)
        decision = app.state.checker.check(claim, moment, doc)
        decision["metric_in_fact_layer"] = body.metric in known_metrics
        return app.state.audit.record(match_id, decision, origin="claims/check")

    @app.get("/matches/{match_id}/audit")
    def get_audit(match_id: str) -> dict:
        data.get_match_doc(match_id)
        entries = app.state.audit.entries(match_id)
        return {"match_id": match_id, "count": len(entries), "entries": entries}

    return app


def _validate_clock(value: str | None, name: str) -> None:
    if value is None:
        return
    try:
        parse_clock(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{name} must be a clock like 55:00") from None


app = create_app()

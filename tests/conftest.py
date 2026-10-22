from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.data import get_fixture, get_match_doc
from api.main import create_app

MATCH_ID = "m-demo-001"
MOMENT_TYPES = {
    "pressure_spell",
    "shot_after_turnovers",
    "momentum_swing",
    "goal",
    "player_milestone",
}


@pytest.fixture(autouse=True)
def _template_explainer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep API tests deterministic even when a local .env enables Foundry."""
    monkeypatch.setenv("MECHI_EXPLAINER", "template")
    monkeypatch.setenv("MECHI_EXPLANATION_CACHE", "")
    monkeypatch.setenv("MECHI_EXPLAINER_PREWARM", "0")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="session")
def match_doc() -> dict:
    return get_match_doc(MATCH_ID)


@pytest.fixture(scope="session")
def fixture_doc() -> dict:
    return get_fixture(MATCH_ID)

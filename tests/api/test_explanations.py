"""Explanation cache, Foundry call settings, and the split narrate / explain routes."""

from __future__ import annotations

import json
import threading
import time

import pytest

from agents.explainer import TemplateExplainer
from agents.foundry import FOUNDATION_NAME, FoundryExplainer
from api import data
from api.claims import AgentsClaimChecker
from api.explanations import ExplanationCache
from api.narration import narrate
from tests.conftest import MATCH_ID


class FakeFoundry:
    """Stands in for ``agents.foundry._complete``; counts model calls."""

    def __init__(self, *, delay: float = 0.0, sentence: str = "Why {metric} matters.", fail: bool = False):
        self.calls = 0
        self.delay = delay
        self.sentence = sentence
        self.fail = fail
        self._lock = threading.Lock()

    def __call__(self, prompt: str) -> str:
        with self._lock:
            self.calls += 1
        time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("endpoint down")
        payload = json.loads(prompt.split("\n\n", 1)[1])
        return json.dumps(
            {
                "summary_en": "The moment that changed the game.",
                "claims": [
                    {"id": c["id"], "sentence": self.sentence.format(metric=c["metric"])}
                    for c in payload["claims"]
                ],
            }
        )


@pytest.fixture()
def foundry(monkeypatch):
    monkeypatch.setenv("MECHI_EXPLAINER", "foundry")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/openai/v1/responses")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
    fake = FakeFoundry()
    monkeypatch.setattr("agents.foundry._complete", fake)
    return fake


@pytest.fixture()
def live_moments() -> dict[str, dict]:
    return {m["id"]: m for m in data.get_moments(MATCH_ID, "live")}


def test_cache_calls_the_model_once_per_moment(foundry, match_doc, live_moments):
    cache = ExplanationCache(None)
    moment = live_moments["mom-pressure-06"]
    checker = AgentsClaimChecker()
    for persona, language in [("analyst", "en"), ("casual", "sw"), ("newcomer", "en")]:
        result = narrate(
            moment, match_doc, persona=persona, language=language, register=None,
            checker=checker, cache=cache,
        )
        assert result["explanation"]["explainer"] == FOUNDATION_NAME
        assert result["explanation"]["summary_en"] == "The moment that changed the game."
    assert foundry.calls == 1
    assert cache.stats()["cached"] == 1


def test_concurrent_requests_share_one_model_call(foundry, live_moments):
    foundry.delay = 0.2
    cache = ExplanationCache(None)
    moment = live_moments["mom-goal-04"]
    results: list[dict] = []
    threads = [
        threading.Thread(target=lambda: results.append(cache.package(MATCH_ID, "live", moment)))
        for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert foundry.calls == 1
    assert {r["explainer"] for r in results} == {FOUNDATION_NAME}


def test_failures_fall_back_are_not_cached_and_cool_down(foundry, live_moments):
    foundry.fail = True
    moment = live_moments["mom-goal-01"]

    cache = ExplanationCache(None, cooldown_s=60)
    first = cache.package(MATCH_ID, "live", moment)
    assert first["explainer"] == "template-v1"
    assert "endpoint down" in first["foundry_error"]
    second = cache.package(MATCH_ID, "live", moment)
    assert "cooling down" in second["foundry_error"]
    assert foundry.calls == 1
    assert cache.stats()["cached"] == 0

    foundry.fail = False
    retry = ExplanationCache(None, cooldown_s=0)
    retry.package(MATCH_ID, "live", moment)
    assert retry.package(MATCH_ID, "live", moment)["explainer"] == FOUNDATION_NAME
    assert foundry.calls == 2


def test_slow_calls_hit_the_deadline_without_cooling_down(foundry, live_moments, monkeypatch):
    monkeypatch.setenv("MECHI_FOUNDRY_TIMEOUT_S", "0.1")
    foundry.delay = 0.5
    cache = ExplanationCache(None, cooldown_s=60)
    moment = live_moments["mom-goal-01"]

    started = time.perf_counter()
    package = cache.package(MATCH_ID, "live", moment)
    assert time.perf_counter() - started < 0.4
    assert package["explainer"] == "template-v1"
    assert package["foundry_error"].startswith("timed out")

    foundry.delay = 0.0
    monkeypatch.setenv("MECHI_FOUNDRY_TIMEOUT_S", "5")
    assert cache.package(MATCH_ID, "live", moment)["explainer"] == FOUNDATION_NAME


def test_disk_cache_survives_a_restart(foundry, live_moments, tmp_path):
    path = tmp_path / "explanations.json"
    moment = live_moments["mom-goal-04"]
    ExplanationCache(path).package(MATCH_ID, "live", moment)
    assert path.is_file()

    restarted = ExplanationCache(path)
    package = restarted.package(MATCH_ID, "live", moment)
    assert package["explainer"] == FOUNDATION_NAME
    assert foundry.calls == 1


def test_prompt_version_and_moment_content_invalidate_the_cache(foundry, live_moments, monkeypatch):
    cache = ExplanationCache(None)
    moment = live_moments["mom-goal-04"]
    cache.package(MATCH_ID, "live", moment)
    monkeypatch.setattr(FoundryExplainer, "prompt_version", "next")
    cache.package(MATCH_ID, "live", moment)
    cache.package(MATCH_ID, "live", {**moment, "headline": {"en": "Edited headline"}})
    assert foundry.calls == 3


def test_template_mode_bypasses_the_cache(foundry, live_moments, monkeypatch):
    monkeypatch.setenv("MECHI_EXPLAINER", "template")
    cache = ExplanationCache(None)
    package = cache.package(MATCH_ID, "live", live_moments["mom-goal-01"])
    assert package.get("explainer", "template-v1") == "template-v1"
    assert foundry.calls == 0
    assert cache.stats()["cached"] == 0
    assert cache.warm(MATCH_ID, [("live", live_moments["mom-goal-01"])]) is None


def test_prewarm_explains_every_moment_in_the_background(foundry, live_moments):
    cache = ExplanationCache(None)
    thread = cache.warm(MATCH_ID, [("live", m) for m in live_moments.values()])
    assert thread is not None
    thread.join(timeout=5)
    stats = cache.stats()
    assert stats["cached"] == len(live_moments)
    assert stats["warm"] == {"total": len(live_moments), "done": len(live_moments), "running": False}
    assert foundry.calls == len(live_moments)


def test_rewrites_with_invented_numbers_keep_the_template_sentence(foundry, live_moments):
    foundry.sentence = "Red Kites forced 99 turnovers, so {metric} matters."
    moment = live_moments["mom-pressure-06"]
    template = TemplateExplainer(MATCH_ID).explain_moment(moment)
    package = ExplanationCache(None).package(MATCH_ID, "live", moment)
    assert [c["sentence"] for c in package["claims"]] == [c["sentence"] for c in template["claims"]]
    assert package["foundry_rejected"] == [c["id"] for c in package["claims"]]


def test_rewrites_may_repeat_fact_layer_numbers(foundry, live_moments):
    foundry.sentence = "Four turnovers in 5.7 minutes ({metric}) broke the Blue Herons press at 61:30."
    package = ExplanationCache(None).package(MATCH_ID, "live", live_moments["mom-pressure-06"])
    assert "foundry_rejected" not in package
    assert package["claims"][0]["sentence"].startswith("Four turnovers in 5.7 minutes")


def test_foundry_client_is_reused_bounded_and_low_effort(monkeypatch, live_moments):
    monkeypatch.setenv("MECHI_EXPLAINER", "foundry")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/openai/v1/responses")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
    monkeypatch.delenv("MECHI_FOUNDRY_TIMEOUT_S", raising=False)
    monkeypatch.delenv("MECHI_FOUNDRY_REASONING", raising=False)
    built: list[dict] = []
    requests: list[dict] = []

    class _Resp:
        output_text = json.dumps({"summary_en": "ok", "claims": []})

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            built.append(kwargs)
            self.responses = self

        def create(self, **kwargs):
            requests.append(kwargs)
            return _Resp()

    monkeypatch.setattr("agents.foundry.OpenAI", _FakeOpenAI)
    explainer = FoundryExplainer(MATCH_ID)
    explainer.explain_moment(live_moments["mom-goal-01"])
    explainer.explain_moment(live_moments["mom-goal-04"])

    assert len(built) == 1
    assert built[0]["timeout"] == 10.0
    assert built[0]["max_retries"] == 0
    assert requests[0]["reasoning"] == {"effort": "minimal"}
    assert requests[0]["max_output_tokens"] == 1000


def test_narrate_without_explain_never_waits_on_the_model(foundry, client):
    res = client.post(
        f"/matches/{MATCH_ID}/narrate",
        json={"moment_id": "mom-goal-04", "persona": "casual", "language": "sw", "source": "live", "explain": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert "explanation" not in body
    assert body["narrative"]["text"]
    assert foundry.calls == 0


def test_narrate_includes_explanation_by_default(client):
    res = client.post(
        f"/matches/{MATCH_ID}/narrate",
        json={"moment_id": "mom-goal-04", "persona": "casual", "language": "en", "source": "live"},
    )
    assert res.json()["explanation"]["moment_id"] == "mom-goal-04"


def test_explain_route_uses_the_requested_source_and_cache(foundry, client):
    url = f"/matches/{MATCH_ID}/moments/mom-pressure-06/explain"
    first = client.get(url, params={"source": "live"})
    second = client.get(url, params={"source": "live"})
    assert first.status_code == 200
    assert first.json()["explainer"] == FOUNDATION_NAME
    assert first.json()["summary"]["blocked"] == 0
    assert second.json() == first.json()
    assert foundry.calls == 1
    assert client.get(f"/matches/{MATCH_ID}/moments/mom-pressure-06/explain").status_code == 404


def test_health_reports_explanation_cache(client):
    explainer = client.get("/health").json()["explainer"]
    assert explainer["active"] == "template-v1"
    assert explainer["cached"] == 0
    assert explainer["warm"] == {"total": 0, "done": 0, "running": False}

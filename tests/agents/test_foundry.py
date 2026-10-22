"""Foundry explainer: rewrite sentences, never change verified numbers, fall back."""

from __future__ import annotations

import json

from agents.explainer import TemplateExplainer
from agents.foundry import FoundryExplainer, explainer_status, make_explainer


def test_make_explainer_defaults_to_template(monkeypatch):
    monkeypatch.delenv("MECHI_EXPLAINER", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    explainer = make_explainer("m-demo-001")
    assert isinstance(explainer, TemplateExplainer)
    assert explainer_status()["active"] == "template-v1"


def test_foundry_rewrites_sentences_without_changing_values(monkeypatch, fixture_doc):
    monkeypatch.setenv("MECHI_EXPLAINER", "foundry")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")

    moment = next(m for m in fixture_doc["moments"] if m["type"] == "pressure_spell")
    original = TemplateExplainer("m-demo-001").explain_moment(moment)
    rewritten = {
        "summary_en": "The press is the story.",
        "claims": [{"id": c["id"], "sentence": f"WHY: {c['metric']}"} for c in original["claims"]],
    }

    class _Msg:
        content = json.dumps(rewritten)

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, **kwargs):
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _FakeAzure:
        def __init__(self, **kwargs):
            self.chat = _Chat()

    monkeypatch.setattr("agents.foundry.AzureOpenAI", _FakeAzure)

    package = FoundryExplainer("m-demo-001").explain_moment(moment)
    assert package["explainer"] == "foundry-gpt-5-mini"
    assert package["summary_en"] == "The press is the story."
    assert package["claims"][0]["value"] == original["claims"][0]["value"]
    assert package["claims"][0]["metric"] == original["claims"][0]["metric"]
    assert package["claims"][0]["sentence"].startswith("WHY:")
    assert explainer_status()["active"] == "foundry-gpt-5-mini"


def test_foundry_uses_responses_api_for_foundry_host(monkeypatch, fixture_doc):
    monkeypatch.setenv("MECHI_EXPLAINER", "foundry")
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/openai/v1/responses"
    )
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")

    moment = next(m for m in fixture_doc["moments"] if m["type"] == "pressure_spell")
    original = TemplateExplainer("m-demo-001").explain_moment(moment)
    rewritten = {
        "summary_en": "Foundry responses path.",
        "claims": [{"id": c["id"], "sentence": f"WHY: {c['metric']}"} for c in original["claims"]],
    }

    class _Resp:
        output_text = json.dumps(rewritten)

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = self

        def create(self, **kwargs):
            return _Resp()

    monkeypatch.setattr("agents.foundry.OpenAI", _FakeOpenAI)

    package = FoundryExplainer("m-demo-001").explain_moment(moment)
    assert package["explainer"] == "foundry-gpt-5-mini"
    assert package["summary_en"] == "Foundry responses path."
    assert package["claims"][0]["sentence"].startswith("WHY:")


def test_foundry_falls_back_on_error(monkeypatch, fixture_doc):
    monkeypatch.setenv("MECHI_EXPLAINER", "foundry")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")

    class _Boom:
        def __init__(self, **kwargs):
            raise RuntimeError("no network")

    monkeypatch.setattr("agents.foundry.AzureOpenAI", _Boom)

    moment = next(m for m in fixture_doc["moments"] if m["type"] == "goal")
    package = FoundryExplainer("m-demo-001").explain_moment(moment)
    assert package["explainer"] == "template-v1"
    assert "foundry_error" in package
    assert package["claims"]

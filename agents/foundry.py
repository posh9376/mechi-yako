"""Microsoft Foundry chat client for the explainer.

Numbers stay on the template fact layer. Foundry only rewrites *why* sentences.
If credentials are missing or the call fails, we keep the template package.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

from agents.explainer import TemplateExplainer

try:
    from openai import AzureOpenAI, OpenAI
except ImportError:  # pragma: no cover — tests still run if extras are missing
    AzureOpenAI = None  # type: ignore[misc, assignment]
    OpenAI = None  # type: ignore[misc, assignment]

EXPLAINER_ENV = "MECHI_EXPLAINER"
FOUNDATION_NAME = "foundry-gpt-5-mini"


def explainer_mode() -> str:
    return (os.environ.get(EXPLAINER_ENV) or "template").strip().lower()


def foundry_configured() -> bool:
    return bool(
        os.environ.get("AZURE_OPENAI_ENDPOINT")
        and os.environ.get("AZURE_OPENAI_API_KEY")
        and os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    )


def explainer_status() -> dict[str, Any]:
    mode = explainer_mode()
    configured = foundry_configured()
    active = FOUNDATION_NAME if mode == "foundry" and configured else "template-v1"
    return {"mode": mode, "configured": configured, "active": active}


class FoundryExplainer:
    name = FOUNDATION_NAME

    def __init__(self, match_id: str) -> None:
        self.match_id = match_id
        self._template = TemplateExplainer(match_id)

    def explain_all(self, moments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.explain_moment(m) for m in moments]

    def explain_moment(self, moment: dict[str, Any]) -> dict[str, Any]:
        package = self._template.explain_moment(moment)
        package["explainer"] = "template-v1"
        if explainer_mode() != "foundry" or not foundry_configured():
            return package
        try:
            rewritten = self._rewrite(moment, package)
        except Exception as exc:  # noqa: BLE001 — live demo must never die on model errors
            package["explainer"] = "template-v1"
            package["foundry_error"] = str(exc)[:240]
            return package
        package["summary_en"] = rewritten.get("summary_en") or package["summary_en"]
        by_id = {c.get("id"): c for c in rewritten.get("claims") or [] if c.get("id")}
        for claim in package["claims"]:
            extra = by_id.get(claim["id"])
            sentence = (extra or {}).get("sentence")
            if isinstance(sentence, str) and sentence.strip():
                claim["sentence"] = sentence.strip()
        package["explainer"] = self.name
        return package

    def _rewrite(self, moment: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "moment_type": moment.get("type"),
            "team": moment.get("team"),
            "t_peak": moment.get("t_peak"),
            "headline": (moment.get("headline") or {}).get("en"),
            "stats": moment.get("stats"),
            "event_ids": moment.get("event_ids"),
            "claims": [
                {
                    "id": c["id"],
                    "metric": c["metric"],
                    "value": c["value"],
                    "sentence": c["sentence"],
                    "event_ids": c.get("event_ids"),
                }
                for c in package["claims"]
            ],
        }
        prompt = (
            "You explain football moments for a broadcast overlay. "
            "Rewrite each claim sentence so it says WHY the moment matters. "
            "Do not change metric, value, id, or event_ids. Do not invent numbers. "
            "Return JSON only: {\"summary_en\": string, \"claims\": [{\"id\": string, \"sentence\": string}]}.\n\n"
            + json.dumps(payload)
        )
        content = _complete(prompt)
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        if not content:
            raise ValueError("foundry returned empty content")
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("foundry response was not a JSON object")
        return data


def _uses_foundry_v1(endpoint: str) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.netloc or ""
    path = parsed.path or ""
    return "services.ai.azure.com" in host or "/openai/v1" in path


def _complete(prompt: str) -> str:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    key = os.environ["AZURE_OPENAI_API_KEY"]
    model = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    if _uses_foundry_v1(endpoint):
        if OpenAI is None:
            raise RuntimeError("openai package is not installed")
        parsed = urlparse(endpoint)
        client = OpenAI(base_url=f"{parsed.scheme}://{parsed.netloc}/openai/v1/", api_key=key)
        resp = client.responses.create(
            model=model,
            instructions="You output JSON only. You never invent statistics.",
            input=prompt,
            max_output_tokens=2000,
            text={"format": {"type": "json_object"}},
        )
        return (getattr(resp, "output_text", None) or "").strip()
    if AzureOpenAI is None:
        raise RuntimeError("openai package is not installed")
    client = AzureOpenAI(
        azure_endpoint=f"{urlparse(endpoint).scheme}://{urlparse(endpoint).netloc}",
        api_key=key,
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-10-21",
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You output JSON only. You never invent statistics.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=400,
    )
    return (resp.choices[0].message.content or "").strip()


def make_explainer(match_id: str) -> TemplateExplainer | FoundryExplainer:
    if explainer_mode() == "foundry" and foundry_configured():
        return FoundryExplainer(match_id)
    return TemplateExplainer(match_id)

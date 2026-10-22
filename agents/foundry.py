"""Microsoft Foundry chat client for the explainer.

Numbers stay on the template fact layer. Foundry only rewrites *why* sentences.
If credentials are missing or the call fails, we keep the template package.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any
from urllib.parse import urlparse

from agents.explainer import TemplateExplainer

try:
    from openai import AzureOpenAI, OpenAI
except ImportError:  # pragma: no cover — tests still run if extras are missing
    AzureOpenAI = None  # type: ignore[misc, assignment]
    OpenAI = None  # type: ignore[misc, assignment]

EXPLAINER_ENV = "MECHI_EXPLAINER"
TIMEOUT_ENV = "MECHI_FOUNDRY_TIMEOUT_S"
REASONING_ENV = "MECHI_FOUNDRY_REASONING"
FOUNDATION_NAME = "foundry-gpt-5-mini"
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_REASONING = "minimal"
MAX_OUTPUT_TOKENS = 1000
TIMED_OUT = "timed out"

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_calls = ThreadPoolExecutor(max_workers=8, thread_name_prefix="foundry")


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


def _timeout_s() -> float:
    try:
        return float(os.environ.get(TIMEOUT_ENV) or DEFAULT_TIMEOUT_S)
    except ValueError:
        return DEFAULT_TIMEOUT_S


def _reasoning_effort() -> str | None:
    value = os.environ.get(REASONING_ENV)
    if value is None:
        return DEFAULT_REASONING
    return value.strip().lower() or None


def _norm(number: str) -> str:
    value = float(number)
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _numbers(*parts: Any) -> set[str]:
    text = " ".join(p if isinstance(p, str) else json.dumps(p) for p in parts if p is not None)
    return {_norm(n) for n in _NUMBER.findall(text)}


class FoundryExplainer:
    name = FOUNDATION_NAME
    # Bump when the prompt or the rewrite rules change, so cached rewrites are discarded.
    prompt_version = "2"

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
        started = time.perf_counter()
        timeout = _timeout_s()
        # The client timeout bounds each network wait, not the whole call; this is the deadline.
        future = _calls.submit(self._rewrite, moment, package)
        try:
            rewritten = future.result(timeout=timeout)
        except FutureTimeout:
            future.cancel()
            package["foundry_error"] = f"{TIMED_OUT} after {timeout:g} s"
            return package
        except Exception as exc:  # noqa: BLE001 — live demo must never die on model errors
            package["explainer"] = "template-v1"
            package["foundry_error"] = str(exc)[:240]
            return package
        package["foundry_ms"] = round((time.perf_counter() - started) * 1000)

        # The model may only restate numbers the fact layer already holds.
        moment_numbers = _numbers(
            moment.get("stats"), (moment.get("headline") or {}).get("en"),
            moment.get("t_start"), moment.get("t_peak"), moment.get("t_end"),
        )
        rejected: list[str] = []
        by_id = {c.get("id"): c for c in rewritten.get("claims") or [] if c.get("id")}
        all_allowed = set(moment_numbers)
        for claim in package["claims"]:
            allowed = moment_numbers | _numbers(claim["sentence"], claim["value"])
            all_allowed |= allowed
            sentence = (by_id.get(claim["id"]) or {}).get("sentence")
            if not isinstance(sentence, str) or not sentence.strip():
                continue
            if _numbers(sentence) <= allowed:
                claim["sentence"] = sentence.strip()
            else:
                rejected.append(claim["id"])
        summary = rewritten.get("summary_en")
        if isinstance(summary, str) and summary.strip():
            if _numbers(summary) <= all_allowed:
                package["summary_en"] = summary.strip()
            else:
                rejected.append("summary_en")
        if rejected:
            package["foundry_rejected"] = rejected
        package["explainer"] = self.name
        return package

    def _rewrite(self, moment: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "moment_type": moment.get("type"),
            "team": moment.get("team"),
            "t_peak": moment.get("t_peak"),
            "headline": (moment.get("headline") or {}).get("en"),
            "stats": moment.get("stats"),
            "claims": [
                {"id": c["id"], "metric": c["metric"], "value": c["value"], "sentence": c["sentence"]}
                for c in package["claims"]
            ],
        }
        prompt = (
            "You explain football moments for a broadcast overlay. "
            "Rewrite each claim sentence so it says WHY the moment matters, in one sentence of at most 25 words. "
            "Do not change metric, value or id. Use only numbers that appear in the input. "
            "Return JSON only: {\"summary_en\": string, \"claims\": [{\"id\": string, \"sentence\": string}]}.\n\n"
            + json.dumps(payload, separators=(",", ":"))
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


_clients: dict[tuple[Any, ...], Any] = {}
_clients_lock = threading.Lock()


def _client(factory: Any, **kwargs: Any) -> Any:
    """One client per configuration, so calls reuse the open HTTPS connection."""
    key = (factory, tuple(sorted(kwargs.items())))
    with _clients_lock:
        client = _clients.get(key)
        if client is None:
            client = factory(**kwargs)
            _clients[key] = client
        return client


def _complete(prompt: str) -> str:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    key = os.environ["AZURE_OPENAI_API_KEY"]
    model = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    parsed = urlparse(endpoint)
    timeout = _timeout_s()
    effort = _reasoning_effort()
    if _uses_foundry_v1(endpoint):
        if OpenAI is None:
            raise RuntimeError("openai package is not installed")
        client = _client(
            OpenAI,
            base_url=f"{parsed.scheme}://{parsed.netloc}/openai/v1/",
            api_key=key,
            timeout=timeout,
            max_retries=0,
        )
        extra: dict[str, Any] = {"reasoning": {"effort": effort}} if effort else {}
        resp = client.responses.create(
            model=model,
            instructions="You output JSON only. You never invent statistics.",
            input=prompt,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            text={"format": {"type": "json_object"}},
            **extra,
        )
        return (getattr(resp, "output_text", None) or "").strip()
    if AzureOpenAI is None:
        raise RuntimeError("openai package is not installed")
    client = _client(
        AzureOpenAI,
        azure_endpoint=f"{parsed.scheme}://{parsed.netloc}",
        api_key=key,
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-10-21",
        timeout=timeout,
        max_retries=0,
    )
    # Reasoning tokens count against max_completion_tokens; too small a budget returns
    # empty content. reasoning_effort is not sent: older api-versions reject it.
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
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )
    return (resp.choices[0].message.content or "").strip()


def make_explainer(match_id: str) -> TemplateExplainer | FoundryExplainer:
    if explainer_mode() == "foundry" and foundry_configured():
        return FoundryExplainer(match_id)
    return TemplateExplainer(match_id)

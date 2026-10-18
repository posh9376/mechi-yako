"""Build the cached demo bundle the web app can run on with the API down.

    python -m api.build_cache            # writes web/public/demo-bundle.json
    python -m api.build_cache --check    # exit 1 if the committed bundle is stale

Shape is documented in docs/cache-bundle.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agents.persona.definitions import LANGUAGES, PERSONAS, REGISTERS
from api import data
from api.claims import AgentsClaimChecker, verify_moment
from api.narration import narrate
from lexicon import load_lexicon
from pipeline.state import MatchStateAggregator

BUNDLE_VERSION = 1
DEFAULT_OUT = data.ROOT / "web" / "public" / "demo-bundle.json"


def build_bundle(match_id: str = "m-demo-001", source: data.MomentSource = "fixture") -> dict[str, Any]:
    doc = data.get_match_doc(match_id)
    moments = data.get_moments(match_id, source)
    checker = AgentsClaimChecker()

    agg = MatchStateAggregator(doc["match"])
    agg.ingest_all(doc["events"])

    narrations: dict[str, Any] = {}
    for moment in moments:
        by_persona: dict[str, Any] = {}
        for persona in PERSONAS:
            by_language: dict[str, Any] = {}
            for language in LANGUAGES:
                by_language[language] = {
                    register: narrate(
                        moment, doc, persona=persona, language=language, register=register, checker=checker
                    )
                    for register in REGISTERS
                }
            by_persona[persona] = by_language
        narrations[moment["id"]] = by_persona

    claims = [d for m in moments for d in verify_moment(m, doc, checker)]
    lexicon = load_lexicon()
    return {
        "bundle_version": BUNDLE_VERSION,
        "schema_version": doc["schema_version"],
        "match_id": match_id,
        "moment_source": source,
        "match": doc["match"],
        "events": doc["events"],
        "final_state": agg.snapshot(),
        "moments": moments,
        "persona_default_register": {p.id: p.default_register for p in PERSONAS.values()},
        "narrations": narrations,
        "claims": {
            "checker": checker.name,
            "summary": {
                s: sum(c["status"] == s for c in claims) for s in ("approved", "corrected", "blocked")
            },
            "claims": claims,
        },
        "lexicon": {"version": lexicon.version, "review": lexicon.review_status},
    }


def _serialise(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, ensure_ascii=False, indent=1) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="Fail if the file on disk is stale")
    args = parser.parse_args(argv)

    text = _serialise(build_bundle())
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.is_file() else ""
        if current != text:
            print(f"{args.out} is stale; run python -m api.build_cache", file=sys.stderr)
            return 1
        print(f"{args.out} is up to date")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out.relative_to(data.ROOT)} ({len(text) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

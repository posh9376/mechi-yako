"""Explain moments → verify claims; demo an injected wrong statistic."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.explainer import TemplateExplainer
from agents.verifier import ClaimVerifier
from pipeline.replay import load_match

DEFAULT_MATCH = ROOT / "data" / "matches" / "m-demo-001.json"
DEFAULT_FIXTURES = ROOT / "data" / "fixtures" / "m-demo-001.moments.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Template explain + verify demo")
    parser.add_argument("--match", type=Path, default=DEFAULT_MATCH)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write explanations + verification + audit log",
    )
    args = parser.parse_args()

    match_doc = load_match(args.match)
    fixtures = json.loads(args.fixtures.read_text(encoding="utf-8"))
    moments = fixtures["moments"]

    explainer = TemplateExplainer(match_doc["match"]["id"])
    verifier = ClaimVerifier(match_doc)

    packages = explainer.explain_all(moments)
    all_results = []
    approved = corrected = blocked = 0

    print(f"Match {match_doc['match']['id']} — {len(moments)} fixture moments\n")
    for pkg in packages:
        print(f"Moment {pkg['moment_id']}: {pkg['summary_en']}")
        results = verifier.verify_all(pkg["claims"])
        for claim, result in zip(pkg["claims"], results):
            all_results.append(result.to_dict())
            mark = result.decision.upper()
            if result.decision == "approved":
                approved += 1
            elif result.decision == "corrected":
                corrected += 1
            else:
                blocked += 1
            print(
                f"  [{mark}] {claim['id']} {claim['metric']}={claim['value']!r} "
                f"— {result.reason}"
            )
        print()

    # Injected wrong stat on the first pressure high_turnovers claim
    sample = None
    for pkg in packages:
        for claim in pkg["claims"]:
            if claim["metric"] == "high_turnovers":
                sample = claim
                break
        if sample:
            break

    injected = None
    if sample:
        injected = verifier.inject_and_verify_wrong_stat(sample, wrong_value=99)
        print("Injected wrong statistic demo")
        print(
            f"  claim {sample['id']} metric={sample['metric']} "
            f"true≈{sample['value']} injected=99 → {injected.decision.upper()}"
        )
        print(f"  reason: {injected.reason}")
        print(f"  audit entries: {len(verifier.audit_log)}")
        if injected.decision == "approved":
            print("ERROR: injected wrong stat was approved")
            return 1
        print("  OK — wrong claim was not approved.\n")

    print(
        f"Summary: approved={approved} corrected={corrected} blocked={blocked} "
        f"(before injection)"
    )

    if args.json_out:
        payload = {
            "schema_version": "1.0",
            "match_id": match_doc["match"]["id"],
            "explanations": packages,
            "verifications": all_results,
            "injected_demo": None if injected is None else injected.to_dict(),
            "audit_log": verifier.audit_log,
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.json_out}")

    # Soft success: at least some approvals; injection must not approve
    if approved == 0:
        print("WARNING: no claims approved — check fixture/stats alignment")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from agents.persona.definitions import LANGUAGES, PERSONAS, REGISTERS
from api.build_cache import build_bundle, main
from tests.conftest import MOMENT_TYPES


def test_bundle_has_every_narration_and_all_pass_qa():
    bundle = build_bundle()
    assert bundle["moment_source"] == "fixture"
    assert {m["type"] for m in bundle["moments"]} == MOMENT_TYPES
    assert len(bundle["events"]) == 123
    assert bundle["final_state"]["score"] == [1, 1]

    for moment in bundle["moments"]:
        by_persona = bundle["narrations"][moment["id"]]
        assert set(by_persona) == set(PERSONAS)
        for persona in PERSONAS:
            assert set(by_persona[persona]) == set(LANGUAGES)
            for language in LANGUAGES:
                assert set(by_persona[persona][language]) == set(REGISTERS)
                for entry in by_persona[persona][language].values():
                    assert entry["qa"]["status"] == "pass", entry


def test_bundle_claim_summary():
    summary = build_bundle()["claims"]["summary"]
    assert summary["blocked"] == 0
    assert summary["corrected"] == 1


def test_committed_bundle_is_fresh():
    assert main(["--check"]) == 0

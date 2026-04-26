"""Tests for regime data integrity."""

from coc_compliance.regimes import REGIMES


class TestRegimeIntegrity:
    def test_all_regimes_have_required_keys(self):
        required = {"name", "description", "log_types", "exclusions", "questions"}
        for key, regime in REGIMES.items():
            missing = required - set(regime.keys())
            assert not missing, f"Regime '{key}' missing keys: {missing}"

    def test_all_regimes_have_log_types(self):
        for key, regime in REGIMES.items():
            assert len(regime["log_types"]) > 0, f"Regime '{key}' has no log types"

    def test_no_empty_names(self):
        for key, regime in REGIMES.items():
            assert regime["name"].strip(), f"Regime '{key}' has empty name"
            assert regime["description"].strip(), f"Regime '{key}' has empty description"

    def test_questions_have_required_fields(self):
        for key, regime in REGIMES.items():
            for q in regime.get("questions", []):
                assert "key" in q, f"Question in '{key}' missing 'key'"
                assert "prompt" in q, f"Question in '{key}' missing 'prompt'"
                assert "type" in q, f"Question in '{key}' missing 'type'"
                assert q["type"] in ("yesno", "text", "choice", "multichoice"), \
                    f"Question '{q['key']}' in '{key}' has invalid type '{q['type']}'"

    def test_choice_questions_have_choices(self):
        for key, regime in REGIMES.items():
            for q in regime.get("questions", []):
                if q["type"] in ("choice", "multichoice"):
                    assert "choices" in q and len(q["choices"]) > 0, \
                        f"Choice question '{q['key']}' in '{key}' has no choices"

    def test_hipaa_exclusion_count(self):
        hipaa = REGIMES["hipaa"]
        assert len(hipaa["exclusions"]) == 15, \
            f"HIPAA has {len(hipaa['exclusions'])} exclusions, expected 15"

    def test_expected_regimes_exist(self):
        expected = ["hipaa", "eu-ai-act", "soc2", "pci-dss", "nist-ai-rmf", "generic-trust", "insurance"]
        for r in expected:
            assert r in REGIMES, f"Expected regime '{r}' not found"

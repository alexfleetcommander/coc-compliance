"""Tests for config generation."""

import json
import os
import tempfile
import pytest

from coc_compliance.config_gen import (
    build_config,
    generate_python_integration,
    generate_js_integration,
    write_config,
    write_integration,
)


class TestBuildConfig:
    def test_single_regime(self):
        config = build_config(regimes=["hipaa"], answers={}, storage="local")
        assert config["version"] == "1.0"
        assert "hipaa" in config["regimes"]
        assert config["regimes"]["hipaa"]["enabled"] is True
        assert len(config["logging"]["log_types"]) > 0
        assert len(config["logging"]["exclusions"]) > 0

    def test_multiple_regimes_merge(self):
        config = build_config(regimes=["hipaa", "soc2"], answers={})
        hipaa_types = len(build_config(regimes=["hipaa"], answers={})["logging"]["log_types"])
        soc2_types = len(build_config(regimes=["soc2"], answers={})["logging"]["log_types"])
        merged_types = len(config["logging"]["log_types"])
        assert merged_types <= hipaa_types + soc2_types
        assert merged_types >= max(hipaa_types, soc2_types)

    def test_answers_stored(self):
        answers = {"hipaa.covered_entity": True, "hipaa.phi_handling": False}
        config = build_config(regimes=["hipaa"], answers=answers)
        assert config["regimes"]["hipaa"]["answers"]["covered_entity"] is True
        assert config["regimes"]["hipaa"]["answers"]["phi_handling"] is False

    def test_local_storage(self):
        config = build_config(regimes=["generic-trust"], answers={}, storage="local", log_path="/tmp/logs/")
        assert config["logging"]["storage"] == "local"
        assert config["logging"]["path"] == "/tmp/logs/"

    def test_hosted_storage(self):
        config = build_config(regimes=["generic-trust"], answers={}, storage="hosted", api_key="test")
        assert config["logging"]["storage"] == "hosted"
        assert config["logging"]["endpoint"] == "https://api.vibeagentmaking.com/coc"
        assert config["logging"]["api_key_env"] == "COC_API_KEY"

    def test_unknown_regime_skipped(self):
        config = build_config(regimes=["nonexistent"], answers={})
        assert config["regimes"] == {}
        assert config["logging"]["log_types"] == []

    def test_encryption_enabled_with_regimes(self):
        config = build_config(regimes=["hipaa"], answers={})
        assert config["encryption"] is True

    def test_empty_regimes(self):
        config = build_config(regimes=[], answers={})
        assert config["regimes"] == {}


class TestGenerateIntegration:
    def test_python_output_is_string(self):
        config = build_config(regimes=["hipaa"], answers={})
        code = generate_python_integration(config)
        assert isinstance(code, str)
        assert "compliance_filter" in code
        assert "import re" in code

    def test_python_compliance_filter_not_noop(self):
        config = build_config(regimes=["hipaa"], answers={})
        code = generate_python_integration(config)
        assert "return True" not in code or "return False" in code
        assert "_EXCLUSION_PATTERNS" in code

    def test_js_output_is_string(self):
        config = build_config(regimes=["soc2"], answers={})
        code = generate_js_integration(config)
        assert isinstance(code, str)
        assert "complianceFilter" in code
        assert "_EXCLUSION_PATTERNS" in code

    def test_js_compliance_filter_not_noop(self):
        config = build_config(regimes=["hipaa"], answers={})
        code = generate_js_integration(config)
        assert "return false" in code.lower()

    def test_langchain_integration(self):
        config = build_config(regimes=["hipaa"], answers={})
        code = generate_python_integration(config, framework="langchain")
        assert "CoCComplianceCallback" in code
        assert "BaseCallbackHandler" in code


class TestWriteConfig:
    def test_writes_valid_json(self):
        config = build_config(regimes=["hipaa"], answers={})
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_config(config, tmpdir)
            assert os.path.exists(path)
            with open(path, "r") as f:
                loaded = json.load(f)
            assert loaded["version"] == "1.0"

    def test_write_permission_error(self):
        config = build_config(regimes=["hipaa"], answers={})
        with pytest.raises(SystemExit, match="Error writing config"):
            write_config(config, "/nonexistent/path/that/does/not/exist")


class TestWriteIntegration:
    def test_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_integration("print('hello')", "test.py", tmpdir)
            assert os.path.exists(path)
            with open(path, "r") as f:
                assert f.read() == "print('hello')"

    def test_write_permission_error(self):
        with pytest.raises(SystemExit, match="Error writing integration"):
            write_integration("code", "test.py", "/nonexistent/path/that/does/not/exist")

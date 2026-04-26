"""Tests for environment detection."""

import tempfile
import os
import json

from coc_compliance.detect import (
    detect_project_type,
    detect_existing_config,
    run_full_detection,
)


class TestDetectProjectType:
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = detect_project_type(tmpdir)
            assert result["languages"] == []
            assert result["files"] == []

    def test_detects_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "requirements.txt"), "w").close()
            result = detect_project_type(tmpdir)
            assert "python" in result["languages"]
            assert "requirements.txt" in result["files"]

    def test_detects_javascript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "package.json"), "w") as f:
                f.write("{}")
            result = detect_project_type(tmpdir)
            assert "javascript" in result["languages"]

    def test_detects_both(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "setup.py"), "w").close()
            with open(os.path.join(tmpdir, "package.json"), "w") as f:
                f.write("{}")
            result = detect_project_type(tmpdir)
            assert "python" in result["languages"]
            assert "javascript" in result["languages"]

    def test_no_duplicate_language(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "setup.py"), "w").close()
            open(os.path.join(tmpdir, "requirements.txt"), "w").close()
            open(os.path.join(tmpdir, "pyproject.toml"), "w").close()
            result = detect_project_type(tmpdir)
            assert result["languages"].count("python") == 1


class TestDetectExistingConfig:
    def test_no_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert detect_existing_config(tmpdir) is None

    def test_finds_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "coc-compliance.json")
            with open(config_path, "w") as f:
                json.dump({"version": "1.0"}, f)
            result = detect_existing_config(tmpdir)
            assert result is not None
            assert result["config"]["version"] == "1.0"

    def test_handles_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "coc-compliance.json")
            with open(config_path, "w") as f:
                f.write("not json")
            result = detect_existing_config(tmpdir)
            assert result is not None
            assert result["config"] is None


class TestRunFullDetection:
    def test_returns_all_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_full_detection(tmpdir)
            assert "model_sdks" in result
            assert "frameworks" in result
            assert "coc_installed" in result
            assert "existing_config" in result
            assert "project" in result

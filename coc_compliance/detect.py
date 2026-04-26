"""Auto-detection of installed model SDKs, agent frameworks, and existing CoC setup."""

import importlib.util
import os
import glob
import json
from pathlib import Path


MODEL_SDKS = {
    "anthropic": {"name": "Anthropic (Claude)", "package": "anthropic"},
    "openai": {"name": "OpenAI", "package": "openai"},
    "google-generativeai": {"name": "Google Generative AI (Gemini)", "package": "google.generativeai"},
    "ollama": {"name": "Ollama", "package": "ollama"},
    "cohere": {"name": "Cohere", "package": "cohere"},
    "mistralai": {"name": "Mistral AI", "package": "mistralai"},
}

AGENT_FRAMEWORKS = {
    "langchain": {"name": "LangChain", "package": "langchain"},
    "crewai": {"name": "CrewAI", "package": "crewai"},
    "autogen": {"name": "AutoGen", "package": "autogen"},
    "semantic-kernel": {"name": "Semantic Kernel", "package": "semantic_kernel"},
    "llama-index": {"name": "LlamaIndex", "package": "llama_index"},
    "haystack": {"name": "Haystack", "package": "haystack"},
    "smolagents": {"name": "Smolagents", "package": "smolagents"},
}

COC_PACKAGES = {
    "chain-of-consciousness": "chain_of_consciousness",
    "agent-trust-stack": "agent_trust_stack",
    "agent-trust-stack-hosted": "agent_trust_hosted",
}


def _check_installed(import_path: str) -> str | None:
    """Return version string if package is importable, else None."""
    spec = importlib.util.find_spec(import_path.split(".")[0])
    if spec is None:
        return None
    try:
        mod = importlib.import_module(import_path)
        return getattr(mod, "__version__", "installed")
    except Exception:
        return "installed"


def detect_model_sdks() -> list[dict]:
    """Return list of detected model SDKs with name, key, and version."""
    found = []
    for key, info in MODEL_SDKS.items():
        version = _check_installed(info["package"])
        if version:
            found.append({"key": key, "name": info["name"], "version": version})
    return found


def detect_frameworks() -> list[dict]:
    """Return list of detected agent frameworks."""
    found = []
    for key, info in AGENT_FRAMEWORKS.items():
        version = _check_installed(info["package"])
        if version:
            found.append({"key": key, "name": info["name"], "version": version})
    return found


def detect_coc() -> dict | None:
    """Check if Chain of Consciousness is already installed. Returns info dict or None."""
    for pkg_name, import_path in COC_PACKAGES.items():
        version = _check_installed(import_path)
        if version:
            return {"package": pkg_name, "version": version}
    return None


def detect_existing_config(search_dir: str = ".") -> dict | None:
    """Look for existing coc-compliance config files in the project."""
    config_names = [
        "coc-compliance.json",
        ".coc-compliance.json",
        "coc_compliance.json",
        ".coc_compliance.json",
    ]
    search = Path(search_dir)
    for name in config_names:
        path = search / name
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return {"path": str(path), "config": json.load(f)}
            except (json.JSONDecodeError, OSError):
                return {"path": str(path), "config": None}

    pyproject = search / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8")
            if "[tool.coc-compliance]" in content:
                return {"path": str(pyproject), "config": "pyproject.toml"}
        except OSError:
            pass

    return None


def detect_project_type(search_dir: str = ".") -> dict:
    """Detect project language and structure hints."""
    search = Path(search_dir)
    hints = {"languages": [], "files": []}

    py_markers = ["setup.py", "setup.cfg", "pyproject.toml", "requirements.txt", "Pipfile"]
    js_markers = ["package.json", "tsconfig.json", "node_modules"]

    for m in py_markers:
        if (search / m).exists():
            if "python" not in hints["languages"]:
                hints["languages"].append("python")
            hints["files"].append(m)

    for m in js_markers:
        if (search / m).exists():
            if "javascript" not in hints["languages"]:
                hints["languages"].append("javascript")
            hints["files"].append(m)

    if not hints["languages"]:
        max_depth = 3
        py_found = False
        js_found = False
        for depth in range(max_depth + 1):
            pattern = "/".join(["*"] * depth) + "/*" if depth > 0 else "*"
            if not py_found and list(search.glob(f"{pattern}.py"))[:1]:
                py_found = True
            if not js_found and (list(search.glob(f"{pattern}.js"))[:1] or list(search.glob(f"{pattern}.ts"))[:1]):
                js_found = True
            if py_found and js_found:
                break
        if py_found:
            hints["languages"].append("python")
        if js_found:
            hints["languages"].append("javascript")

    return hints


def run_full_detection(search_dir: str = ".") -> dict:
    """Run all detection and return a combined report."""
    return {
        "model_sdks": detect_model_sdks(),
        "frameworks": detect_frameworks(),
        "coc_installed": detect_coc(),
        "existing_config": detect_existing_config(search_dir),
        "project": detect_project_type(search_dir),
    }

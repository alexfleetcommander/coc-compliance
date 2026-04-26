"""Generate compliance configuration files and integration code."""

import json
import os
from pathlib import Path
from .regimes import REGIMES


def build_config(
    regimes: list[str],
    answers: dict,
    storage: str = "local",
    api_key: str | None = None,
    log_path: str = "./coc_logs/",
) -> dict:
    """Build the coc-compliance.json config from user selections."""
    merged_log_types = []
    merged_exclusions = []
    regime_configs = {}

    for regime_key in regimes:
        regime = REGIMES.get(regime_key)
        if not regime:
            continue

        for lt in regime["log_types"]:
            if lt not in merged_log_types:
                merged_log_types.append(lt)

        for ex in regime["exclusions"]:
            if ex not in merged_exclusions:
                merged_exclusions.append(ex)

        regime_answers = {}
        for q in regime.get("questions", []):
            full_key = f"{regime_key}.{q['key']}"
            if full_key in answers:
                regime_answers[q["key"]] = answers[full_key]

        regime_configs[regime_key] = {
            "name": regime["name"],
            "enabled": True,
            "answers": regime_answers,
        }

    config = {
        "version": "1.0",
        "regimes": regime_configs,
        "logging": {
            "storage": storage,
            "log_types": merged_log_types,
            "exclusions": merged_exclusions,
        },
        "encryption": storage != "local" or len(regimes) > 0,
    }

    if storage == "local":
        config["logging"]["path"] = log_path
    elif storage in ("free-hosted", "hosted"):
        config["logging"]["endpoint"] = "https://api.vibeagentmaking.com/coc"
        if api_key:
            config["logging"]["api_key_env"] = "COC_API_KEY"

    return config


def generate_python_integration(config: dict, framework: str | None = None) -> str:
    """Generate Python integration snippet."""
    regimes_list = list(config.get("regimes", {}).keys())
    regime_str = json.dumps(regimes_list)
    storage = config.get("logging", {}).get("storage", "local")

    lines = [
        "import os",
        "import json",
        "",
    ]

    if storage in ("free-hosted", "hosted"):
        lines += [
            "from agent_trust_hosted import TrustClient",
            "",
            "client = TrustClient(api_key=os.environ.get('COC_API_KEY', ''))",
            "",
        ]
    else:
        lines += [
            "from chain_of_consciousness import CoC",
            "",
        ]

    lines.append("# Load compliance config")
    lines.append('with open("coc-compliance.json", "r") as f:')
    lines.append("    compliance_config = json.load(f)")
    lines.append("")

    if storage not in ("free-hosted", "hosted"):
        log_path = config.get("logging", {}).get("path", "./coc_logs/")
        lines.append(f'coc = CoC(storage="local", path="{log_path}", encryption=True)')
    else:
        lines.append("# Hosted CoC — entries go to api.vibeagentmaking.com")
        lines.append("# Chain creation and entry appending via client.coc.*")

    lines.append("")
    lines.append("import re")
    lines.append("")
    lines.append("# Regex patterns mapped to exclusion descriptions from compliance config")
    lines.append("_EXCLUSION_PATTERNS = {")
    lines.append("    'Patient names': r'(?i)\\\\bpatient\\\\s*name\\\\s*[:=]\\\\s*\\\\S+',")
    lines.append("    'Social Security numbers': r'\\\\b\\\\d{3}-\\\\d{2}-\\\\d{4}\\\\b',")
    lines.append("    'Phone and fax numbers': r'\\\\b\\\\d{3}[-.\\\\s]?\\\\d{3}[-.\\\\s]?\\\\d{4}\\\\b',")
    lines.append("    'Email addresses (in health context)': r'[\\\\w.+-]+@[\\\\w-]+\\\\.[\\\\w.-]+',")
    lines.append("    'Web URLs and IP addresses': r'https?://\\\\S+|\\\\b\\\\d{1,3}\\\\.\\\\d{1,3}\\\\.\\\\d{1,3}\\\\.\\\\d{1,3}\\\\b',")
    lines.append("    'Full card numbers (Primary Account Numbers) -- mask to first 6 / last 4 only': r'\\\\b(?:\\\\d[ -]*?){13,19}\\\\b',")
    lines.append("    'Card verification values (CVV, CVC, CID)': r'(?i)\\\\b(?:cvv|cvc|cid)\\\\s*[:=]\\\\s*\\\\d{3,4}\\\\b',")
    lines.append("    'PINs and PIN blocks': r'(?i)\\\\bpin\\\\s*[:=]\\\\s*\\\\d{4,}\\\\b',")
    lines.append("    'Authentication credentials (passwords, tokens, keys)': r'(?i)(?:password|token|secret|api_key)\\\\s*[:=]\\\\s*\\\\S+',")
    lines.append("}")
    lines.append("")
    lines.append("def _build_exclusion_regexes():")
    lines.append("    active_exclusions = compliance_config.get('logging', {}).get('exclusions', [])")
    lines.append("    patterns = []")
    lines.append("    for desc in active_exclusions:")
    lines.append("        if desc in _EXCLUSION_PATTERNS:")
    lines.append("            patterns.append(re.compile(_EXCLUSION_PATTERNS[desc]))")
    lines.append("    return patterns")
    lines.append("")
    lines.append("_active_regexes = _build_exclusion_regexes()")
    lines.append("")
    lines.append("def compliance_filter(entry_data: str) -> bool:")
    lines.append('    """Return False if entry contains data matching any active exclusion pattern."""')
    lines.append("    for pattern in _active_regexes:")
    lines.append("        if pattern.search(entry_data):")
    lines.append("            return False")
    lines.append("    return True")
    lines.append("")

    if framework == "langchain":
        lines += [
            "# LangChain integration — add as a callback",
            "from langchain.callbacks.base import BaseCallbackHandler",
            "",
            "class CoCComplianceCallback(BaseCallbackHandler):",
            "    def on_llm_end(self, response, **kwargs):",
            '        text = response.generations[0][0].text if response.generations else ""',
            "        if compliance_filter(text):",
            "            coc.append(data=text, entry_type='llm_output')",
            "",
        ]
    elif framework == "crewai":
        lines += [
            "# CrewAI integration — wrap task execution",
            "# Add coc.append() calls in your task callbacks",
            "",
        ]

    lines.append(f"print('Compliance configured: {regime_str}')")
    return "\n".join(lines)


def generate_js_integration(config: dict, framework: str | None = None) -> str:
    """Generate JavaScript/Node.js integration snippet."""
    regimes_list = list(config.get("regimes", {}).keys())
    storage = config.get("logging", {}).get("storage", "local")

    lines = [
        "const fs = require('fs');",
        "",
        "const complianceConfig = JSON.parse(",
        "  fs.readFileSync('coc-compliance.json', 'utf-8')",
        ");",
        "",
    ]

    if storage in ("free-hosted", "hosted"):
        lines += [
            "const { TrustClient } = require('agent-trust-stack-hosted');",
            "",
            "const client = new TrustClient({",
            "  apiKey: process.env.COC_API_KEY || '',",
            "});",
            "",
        ]
    else:
        lines += [
            "const { CoC } = require('chain-of-consciousness');",
            "",
            "const coc = new CoC({",
            f"  storage: 'local',",
            f"  path: '{config.get('logging', {}).get('path', './coc_logs/')}',",
            "  encryption: true,",
            "});",
            "",
        ]

    lines.append("const _EXCLUSION_PATTERNS = {")
    lines.append("  'Patient names': /\\bpatient\\s*name\\s*[:=]\\s*\\S+/i,")
    lines.append("  'Social Security numbers': /\\b\\d{3}-\\d{2}-\\d{4}\\b/,")
    lines.append("  'Phone and fax numbers': /\\b\\d{3}[-.\\s]?\\d{3}[-.\\s]?\\d{4}\\b/,")
    lines.append("  'Email addresses (in health context)': /[\\w.+-]+@[\\w-]+\\.[\\w.-]+/,")
    lines.append("  'Web URLs and IP addresses': /https?:\\/\\/\\S+|\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/,")
    lines.append("  'Full card numbers (Primary Account Numbers) -- mask to first 6 / last 4 only': /\\b(?:\\d[ -]*?){13,19}\\b/,")
    lines.append("  'Card verification values (CVV, CVC, CID)': /\\b(?:cvv|cvc|cid)\\s*[:=]\\s*\\d{3,4}\\b/i,")
    lines.append("  'PINs and PIN blocks': /\\bpin\\s*[:=]\\s*\\d{4,}\\b/i,")
    lines.append("  'Authentication credentials (passwords, tokens, keys)': /(?:password|token|secret|api_key)\\s*[:=]\\s*\\S+/i,")
    lines.append("};")
    lines.append("")
    lines.append("const _activeRegexes = (complianceConfig.logging?.exclusions || []).reduce((acc, desc) => {")
    lines.append("  if (_EXCLUSION_PATTERNS[desc]) acc.push(_EXCLUSION_PATTERNS[desc]);")
    lines.append("  return acc;")
    lines.append("}, []);")
    lines.append("")
    lines.append("function complianceFilter(entryData) {")
    lines.append("  for (const pattern of _activeRegexes) {")
    lines.append("    if (pattern.test(entryData)) return false;")
    lines.append("  }")
    lines.append("  return true;")
    lines.append("}")
    lines.append("")
    lines.append(f"console.log('Compliance configured:', {json.dumps(regimes_list)});")
    lines.append("module.exports = { complianceFilter, complianceConfig };")

    return "\n".join(lines)


def write_config(config: dict, output_dir: str = ".") -> str:
    """Write coc-compliance.json to disk. Returns the file path."""
    path = Path(output_dir) / "coc-compliance.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        raise SystemExit(f"Error writing config to {path}: {e}") from e
    return str(path)


def write_integration(code: str, filename: str, output_dir: str = ".") -> str:
    """Write integration snippet to disk. Returns the file path."""
    path = Path(output_dir) / filename
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
    except OSError as e:
        raise SystemExit(f"Error writing integration file to {path}: {e}") from e
    return str(path)

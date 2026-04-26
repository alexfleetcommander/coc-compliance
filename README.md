# coc-compliance

Auto-detect your agent setup and configure Chain of Consciousness (CoC) compliance logging.

Supports 7 compliance regimes: HIPAA, EU AI Act, SOC 2, PCI-DSS, NIST AI RMF, Generic Trust, and Insurance.

## Install

```bash
pip install coc-compliance
```

## Quick Start

```bash
coc-compliance init
```

The wizard will:

1. **Scan** your environment for installed model SDKs (Anthropic, OpenAI, Google, Ollama, etc.) and agent frameworks (LangChain, CrewAI, AutoGen, etc.)
2. **Detect** any existing CoC installation
3. **Present** a checklist of compliance regimes to select
4. **Ask** regime-specific questions (PHI handling, risk classification, trust criteria, etc.)
5. **Generate** a `coc-compliance.json` config and integration code
6. **Install** CoC if not already present
7. **Output** a summary of what was configured and next steps

## Commands

| Command | Description |
|---------|-------------|
| `coc-compliance init` | Interactive setup wizard |
| `coc-compliance detect` | Scan environment only |
| `coc-compliance verify` | Check existing setup for issues |
| `coc-compliance regimes` | List available compliance regimes |

### Options

```
coc-compliance init --dir ./my-project    # Target a specific directory
coc-compliance init --verbose             # Show pip install output
coc-compliance detect --json              # Output detection as JSON
coc-compliance regimes --json             # Output regimes as JSON
```

## Supported Compliance Regimes

| Regime | Key | Description |
|--------|-----|-------------|
| HIPAA | `hipaa` | Healthcare data protection — excludes 15 PHI identifier categories |
| EU AI Act | `eu-ai-act` | AI transparency, risk classification, bias monitoring |
| SOC 2 | `soc2` | Trust services criteria (security, availability, integrity, confidentiality, privacy) |
| PCI-DSS | `pci-dss` | Payment card data — masks PANs, blocks CVV/PIN logging |
| NIST AI RMF | `nist-ai-rmf` | AI risk management (Govern, Map, Measure, Manage) |
| Generic Trust | `generic-trust` | Basic transparency — reasoning, decisions, errors |
| Insurance | `insurance` | Claims/underwriting — protects policyholder PII |

## Output Files

After running `init`, you'll get:

- **`coc-compliance.json`** — Configuration file with selected regimes, log types, and exclusions
- **`coc_compliance_init.py`** (or `.js`) — Integration code snippet to import into your project
- **`./coc_logs/`** — Log directory (if using local storage) with `.gitignore`

## Storage Options

| Option | Description |
|--------|-------------|
| `local` | Logs stored on disk in `./coc_logs/` (default) |
| `free-hosted` | Free tier on api.vibeagentmaking.com (5 anchors/day) |
| `hosted` | Full hosted CoC with auto-anchoring |

For hosted options, set the `COC_API_KEY` environment variable.

## Auto-Detection

The tool detects:

**Model SDKs:** Anthropic (Claude), OpenAI, Google Generative AI, Ollama, Cohere, Mistral AI

**Frameworks:** LangChain, CrewAI, AutoGen, Semantic Kernel, LlamaIndex, Haystack, Smolagents

**CoC Packages:** chain-of-consciousness, agent-trust-stack, agent-trust-stack-hosted

## Cross-Platform

Works on Windows, macOS, and Linux. Python 3.10+.

## Config Format

```json
{
  "version": "1.0",
  "regimes": {
    "hipaa": {
      "name": "HIPAA",
      "enabled": true,
      "answers": {
        "covered_entity": true,
        "phi_handling": true
      }
    }
  },
  "logging": {
    "storage": "local",
    "path": "./coc_logs/",
    "log_types": ["Access events (who accessed what data, when)", "..."],
    "exclusions": ["Patient names", "Social Security numbers", "..."]
  },
  "encryption": true
}
```

## License

MIT

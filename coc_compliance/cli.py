"""Interactive CLI wizard for coc-compliance setup."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from .detect import run_full_detection, COC_PACKAGES
from .regimes import REGIMES
from .config_gen import (
    build_config,
    generate_python_integration,
    generate_js_integration,
    write_config,
    write_integration,
)


# ── Terminal helpers ──────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"

if sys.platform == "win32":
    os.system("")  # enable ANSI on Windows


def _print_header(text: str) -> None:
    width = max(len(text) + 4, 50)
    print(f"\n{CYAN}{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}{RESET}\n")


def _print_step(n: int, total: int, text: str) -> None:
    print(f"\n{BOLD}[Step {n}/{total}] {text}{RESET}")
    print(f"{DIM}{'-' * 50}{RESET}")


def _ask_yesno(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        resp = input(f"{prompt}{suffix}").strip().lower()
        if resp == "":
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("  Please enter y or n.")


def _ask_text(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]: " if default else ": "
    resp = input(f"{prompt}{suffix}").strip()
    return resp if resp else default


def _ask_choice(prompt: str, choices: list[str], default: str | None = None) -> str:
    print(f"{prompt}")
    for i, c in enumerate(choices, 1):
        marker = " (default)" if c == default else ""
        print(f"  {i}. {c}{marker}")
    while True:
        resp = input("Enter number: ").strip()
        if resp == "" and default:
            return default
        try:
            idx = int(resp)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(choices)}.")


def _ask_multichoice(prompt: str, choices: list[str]) -> list[str]:
    print(f"{prompt}")
    for i, c in enumerate(choices, 1):
        print(f"  {i}. {c}")
    print(f"  {DIM}Enter numbers separated by commas, or 'all'{RESET}")
    while True:
        resp = input("Selection: ").strip().lower()
        if resp == "all":
            return list(choices)
        try:
            indices = [int(x.strip()) for x in resp.split(",") if x.strip()]
            if all(1 <= i <= len(choices) for i in indices) and indices:
                return [choices[i - 1] for i in indices]
        except ValueError:
            pass
        print(f"  Please enter comma-separated numbers (1-{len(choices)}) or 'all'.")


def _ask_regime_selection() -> list[str]:
    """Present checkbox-style regime selection."""
    keys = list(REGIMES.keys())
    print(f"\n{BOLD}Available compliance regimes:{RESET}\n")
    for i, key in enumerate(keys, 1):
        regime = REGIMES[key]
        print(f"  {CYAN}{i:2d}.{RESET} {regime['name']:<20s} {DIM}{regime['description']}{RESET}")
    print(f"\n  {DIM}Enter numbers separated by commas, or 'all'{RESET}")

    while True:
        resp = input(f"\n{BOLD}Select regimes: {RESET}").strip().lower()
        if resp == "all":
            return list(keys)
        try:
            indices = [int(x.strip()) for x in resp.split(",") if x.strip()]
            if all(1 <= i <= len(keys) for i in indices) and indices:
                return [keys[i - 1] for i in indices]
        except ValueError:
            pass
        print(f"  Please enter comma-separated numbers (1-{len(keys)}) or 'all'.")


# ── Main flow ─────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> None:
    """Interactive init wizard."""
    _print_header(f"coc-compliance v{__version__} — Setup Wizard")

    total_steps = 6

    # Step 1: Detection
    _print_step(1, total_steps, "Scanning your environment")
    detection = run_full_detection(args.dir)

    sdks = detection["model_sdks"]
    frameworks = detection["frameworks"]
    coc = detection["coc_installed"]
    existing = detection["existing_config"]
    project = detection["project"]

    if sdks:
        print(f"\n  {GREEN}Model SDKs found:{RESET}")
        for s in sdks:
            print(f"    - {s['name']} (v{s['version']})")
    else:
        print(f"\n  {YELLOW}No model SDKs detected.{RESET}")
        print(f"  {DIM}Supported: anthropic, openai, google-generativeai, ollama, cohere, mistralai{RESET}")

    if frameworks:
        print(f"\n  {GREEN}Agent frameworks found:{RESET}")
        for f in frameworks:
            print(f"    - {f['name']} (v{f['version']})")
    else:
        print(f"\n  {DIM}No agent frameworks detected (not required).{RESET}")

    if coc:
        print(f"\n  {GREEN}CoC already installed:{RESET} {coc['package']} v{coc['version']}")
    else:
        print(f"\n  {YELLOW}CoC not installed yet.{RESET}")

    if existing:
        print(f"\n  {YELLOW}Existing config found:{RESET} {existing['path']}")
        if args.force:
            print(f"  {DIM}--force: overwriting existing config.{RESET}")
        elif not _ask_yesno("  Overwrite existing configuration?", default=False):
            print("  Keeping existing config. Run with --force to override.")
            return

    if project["languages"]:
        print(f"\n  {GREEN}Project languages:{RESET} {', '.join(project['languages'])}")

    # Step 2: Regime selection
    _print_step(2, total_steps, "Select compliance regimes")
    selected_regimes = _ask_regime_selection()

    print(f"\n  {GREEN}Selected:{RESET} {', '.join(REGIMES[r]['name'] for r in selected_regimes)}")

    # Step 3: Regime-specific questions
    _print_step(3, total_steps, "Compliance questions")
    answers = {}
    has_questions = False

    for regime_key in selected_regimes:
        regime = REGIMES[regime_key]
        questions = regime.get("questions", [])
        if not questions:
            continue
        has_questions = True
        print(f"\n  {BOLD}{regime['name']} questions:{RESET}")
        for q in questions:
            full_key = f"{regime_key}.{q['key']}"
            if q["type"] == "yesno":
                answers[full_key] = _ask_yesno(f"  {q['prompt']}")
            elif q["type"] == "text":
                answers[full_key] = _ask_text(f"  {q['prompt']}")
            elif q["type"] == "choice":
                answers[full_key] = _ask_choice(f"  {q['prompt']}", q["choices"])
            elif q["type"] == "multichoice":
                answers[full_key] = _ask_multichoice(f"  {q['prompt']}", q["choices"])

    if not has_questions:
        print(f"  {DIM}No additional questions for selected regimes.{RESET}")

    # Step 4: Storage configuration
    _print_step(4, total_steps, "Storage configuration")
    storage_choices = ["local", "free-hosted", "hosted"]
    storage = _ask_choice(
        "  Where should compliance logs be stored?",
        storage_choices,
        default="local",
    )

    api_key = None
    if storage in ("free-hosted", "hosted"):
        api_key = _ask_text(
            "  API key (or set COC_API_KEY env var later)",
            default="",
        )

    log_path = "./coc_logs/"
    if storage == "local":
        log_path = _ask_text("  Log directory path", default="./coc_logs/")

    # Step 5: Install CoC if needed
    _print_step(5, total_steps, "Installing dependencies")

    if not coc:
        if storage in ("free-hosted", "hosted"):
            pkg = "agent-trust-stack-hosted"
        else:
            pkg = "chain-of-consciousness"

        print(f"  Installing {pkg}...")
        if _ask_yesno(f"  Run: pip install {pkg}?"):
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg],
                    stdout=subprocess.DEVNULL if not args.verbose else None,
                )
                print(f"  {GREEN}Installed {pkg} successfully.{RESET}")
            except subprocess.CalledProcessError:
                print(f"  {RED}Failed to install {pkg}. You can install it manually later.{RESET}")
        else:
            print(f"  {DIM}Skipped. Install manually: pip install {pkg}{RESET}")
    else:
        print(f"  {GREEN}CoC already installed — nothing to do.{RESET}")

    # Step 6: Generate and write config
    _print_step(6, total_steps, "Generating configuration")

    config = build_config(
        regimes=selected_regimes,
        answers=answers,
        storage=storage,
        api_key=api_key,
        log_path=log_path,
    )

    output_dir = args.dir
    config_path = write_config(config, output_dir)
    print(f"  {GREEN}Config written:{RESET} {config_path}")

    # Generate integration snippet
    lang = None
    if project["languages"]:
        if len(project["languages"]) == 1:
            lang = project["languages"][0]
        else:
            lang = _ask_choice(
                "  Generate integration code for which language?",
                project["languages"],
            )
    elif sdks or frameworks:
        lang = "python"
    else:
        lang = _ask_choice(
            "  Generate integration code for which language?",
            ["python", "javascript"],
            default="python",
        )

    framework_key = None
    if frameworks:
        framework_key = frameworks[0]["key"]

    if lang == "python":
        code = generate_python_integration(config, framework_key)
        snippet_path = write_integration(code, "coc_compliance_init.py", output_dir)
    else:
        code = generate_js_integration(config, framework_key)
        snippet_path = write_integration(code, "coc_compliance_init.js", output_dir)

    print(f"  {GREEN}Integration code:{RESET} {snippet_path}")

    # Create log directory if local
    if storage == "local":
        log_dir = Path(output_dir) / log_path
        log_dir.mkdir(parents=True, exist_ok=True)
        gitignore = log_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")
        print(f"  {GREEN}Log directory created:{RESET} {log_dir}")

    # Summary
    _print_header("Setup Complete")
    print(f"  {BOLD}Compliance regimes:{RESET} {', '.join(REGIMES[r]['name'] for r in selected_regimes)}")
    print(f"  {BOLD}Storage:{RESET} {storage}")
    print(f"  {BOLD}Config:{RESET} {config_path}")
    print(f"  {BOLD}Integration:{RESET} {snippet_path}")
    print(f"  {BOLD}Log types:{RESET} {len(config['logging']['log_types'])} configured")
    print(f"  {BOLD}Exclusions:{RESET} {len(config['logging']['exclusions'])} patterns")
    print()

    print(f"  {BOLD}Next steps:{RESET}")
    print(f"  1. Review {config_path}")
    print(f"  2. Import the integration code from {snippet_path}")
    print(f"  3. Run {CYAN}coc-compliance verify{RESET} to check your setup")
    if api_key:
        print(f"  4. Set environment variable: export COC_API_KEY=<your-key>")
    print()


def cmd_detect(args: argparse.Namespace) -> None:
    """Run detection only and print results."""
    _print_header("Environment Detection")
    detection = run_full_detection(args.dir)

    if args.json:
        print(json.dumps(detection, indent=2))
        return

    for category, items in [
        ("Model SDKs", detection["model_sdks"]),
        ("Agent Frameworks", detection["frameworks"]),
    ]:
        print(f"\n  {BOLD}{category}:{RESET}")
        if items:
            for item in items:
                print(f"    {GREEN}+{RESET} {item['name']} (v{item['version']})")
        else:
            print(f"    {DIM}(none detected){RESET}")

    coc = detection["coc_installed"]
    print(f"\n  {BOLD}CoC:{RESET}", end=" ")
    if coc:
        print(f"{GREEN}{coc['package']} v{coc['version']}{RESET}")
    else:
        print(f"{YELLOW}not installed{RESET}")

    existing = detection["existing_config"]
    print(f"  {BOLD}Existing config:{RESET}", end=" ")
    if existing:
        print(f"{existing['path']}")
    else:
        print(f"{DIM}none{RESET}")

    project = detection["project"]
    if project["languages"]:
        print(f"  {BOLD}Languages:{RESET} {', '.join(project['languages'])}")
    print()


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify an existing compliance setup."""
    _print_header("Compliance Verification")
    detection = run_full_detection(args.dir)

    issues = []
    warnings = []

    existing = detection["existing_config"]
    if not existing:
        issues.append("No coc-compliance.json config file found. Run: coc-compliance init")
    elif existing["config"] is None:
        issues.append(f"Config file {existing['path']} exists but is not valid JSON")
    else:
        config = existing["config"]
        if isinstance(config, dict):
            regimes = config.get("regimes", {})
            if not regimes:
                warnings.append("No compliance regimes configured")
            logging_cfg = config.get("logging", {})
            if not logging_cfg.get("log_types"):
                warnings.append("No log types configured")
            if not logging_cfg.get("exclusions"):
                warnings.append("No exclusions configured — data may be logged without filtering")

            storage = logging_cfg.get("storage", "local")
            if storage == "local":
                log_path = logging_cfg.get("path", "./coc_logs/")
                full_path = Path(args.dir) / log_path
                if not full_path.exists():
                    warnings.append(f"Log directory does not exist: {log_path}")

            if storage in ("free-hosted", "hosted"):
                if not os.environ.get("COC_API_KEY") and not logging_cfg.get("api_key_env"):
                    warnings.append("Hosted storage selected but COC_API_KEY not set")

    if not detection["coc_installed"]:
        issues.append("CoC package not installed. Run: pip install chain-of-consciousness")

    if issues:
        print(f"  {RED}{BOLD}Issues ({len(issues)}):{RESET}")
        for issue in issues:
            print(f"    {RED}x{RESET} {issue}")
    else:
        print(f"  {GREEN}No blocking issues found.{RESET}")

    if warnings:
        print(f"\n  {YELLOW}{BOLD}Warnings ({len(warnings)}):{RESET}")
        for w in warnings:
            print(f"    {YELLOW}!{RESET} {w}")

    if not issues and not warnings:
        print(f"\n  {GREEN}{BOLD}All checks passed.{RESET} Your compliance setup looks good.")
    elif not issues:
        print(f"\n  {GREEN}Setup is functional{RESET} but review warnings above.")

    print()


def cmd_regimes(args: argparse.Namespace) -> None:
    """List available compliance regimes."""
    if args.json:
        print(json.dumps({k: {"name": v["name"], "description": v["description"]} for k, v in REGIMES.items()}, indent=2))
        return

    _print_header("Available Compliance Regimes")
    for key, regime in REGIMES.items():
        print(f"  {CYAN}{key:<16s}{RESET} {regime['name']}")
        print(f"  {DIM}{' ' * 16} {regime['description']}{RESET}")
        print(f"  {' ' * 16} Log types: {len(regime['log_types'])}, Exclusions: {len(regime['exclusions'])}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="coc-compliance",
        description="Auto-detect your agent setup and configure Chain of Consciousness compliance logging.",
    )
    parser.add_argument("--version", action="version", version=f"coc-compliance {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Interactive compliance setup wizard")
    init_parser.add_argument("--dir", default=".", help="Project directory (default: current)")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config without prompting")
    init_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # detect
    detect_parser = subparsers.add_parser("detect", help="Scan environment and report findings")
    detect_parser.add_argument("--dir", default=".", help="Project directory (default: current)")
    detect_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Verify existing compliance setup")
    verify_parser.add_argument("--dir", default=".", help="Project directory (default: current)")

    # regimes
    regimes_parser = subparsers.add_parser("regimes", help="List available compliance regimes")
    regimes_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        if args.command == "init":
            cmd_init(args)
        elif args.command == "detect":
            cmd_detect(args)
        elif args.command == "verify":
            cmd_verify(args)
        elif args.command == "regimes":
            cmd_regimes(args)
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Setup cancelled.{RESET}")
        sys.exit(130)


if __name__ == "__main__":
    main()

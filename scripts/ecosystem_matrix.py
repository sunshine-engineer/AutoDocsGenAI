# File: scripts/ecosystem_matrix.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Run offline contracts in disposable exact-version environments using uv."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

CASES = (
    ("legacy", "0.3.30", "0.6.11"),
    ("previous", "1.2.18", "1.1.10"),
    ("intermediate", "1.3.18", "1.2.15"),
    ("current", "1.4.6", "1.2.15"),
    ("incompatible", "1.3.18", "1.1.10"),
)


def assess(results: list[dict], output: Path) -> list[str]:
    """Evaluate expected successes and known compatibility failures from probe results.

    Args:
        results: Recorded compatibility probe results.
        output: Destination for newly generated artifacts or reports.

    Returns:
        Unexpected compatibility outcomes requiring operator review; empty means
        expected contracts held.
    """
    unexpected = []
    for row in results:
        label = str(row["label"])
        if label == "incompatible":
            if row["install_exit"] == 0:
                unexpected.append(
                    "Previously incompatible pair now resolves; review dependency changes"
                )
            else:
                log = (output / "incompatible-install.log").read_text()
                if (
                    "No solution found" not in log
                    or "langgraph>=1.2.11,<1.3.0" not in log
                ):
                    unexpected.append(
                        "Incompatible installation failed for an unrecognized reason"
                    )
            continue
        if row["install_exit"] != 0 or row.get("probe_exit") != 0:
            unexpected.append(label + ": setup or probe failure")
            continue
        checks = json.loads((output / f"{label}.json").read_text())["checks"]
        required = {
            "runnable_chain",
            "state_graph_checkpoint_stream",
            "local_tool_node",
            "graph_tool_node",
            "modern_create_agent",
        }
        if {check["name"] for check in checks} != required or len(checks) != len(
            required
        ):
            unexpected.append(label + ": incomplete or duplicate checks")
        for check in checks:
            expected = (
                "failed"
                if (check["name"] == "modern_create_agent" and label == "legacy")
                or (check["name"] == "local_tool_node" and label != "legacy")
                else "passed"
            )
            known_error = (
                "ImportError: cannot import name 'create_agent'"
                if check["name"] == "modern_create_agent"
                else "ValueError: Missing required config key"
            )
            if check["status"] != expected or (
                expected == "failed"
                and not check.get("error", "").startswith(known_error)
            ):
                unexpected.append(label + ": unexpected outcome for " + check["name"])
    return unexpected


def main():
    """Parse command-line inputs and run the ecosystem matrix operator command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-root", type=Path, required=True)
    parser.add_argument("--uv", default="uv")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    args.env_root.mkdir(parents=True, exist_ok=False)
    probe = Path(__file__).with_name("ecosystem_probe.py").resolve()
    results = []
    clean = {
        key: value
        for key, value in os.environ.items()
        if key
        in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "SystemRoot")
    }
    clean.update(LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false")
    for label, langchain, langgraph in CASES:
        env = args.env_root / label
        subprocess.run(
            [args.uv, "venv", str(env), "--python", "3.12"],
            check=True,
            capture_output=True,
            timeout=120,
        )
        python = env / (
            "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
        )
        install = subprocess.run(
            [
                args.uv,
                "pip",
                "install",
                "--python",
                str(python),
                f"langchain=={langchain}",
                f"langgraph=={langgraph}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=360,
        )
        (args.output / f"{label}-install.log").write_text(
            install.stdout + install.stderr, encoding="utf-8"
        )
        row = {
            "label": label,
            "langchain": langchain,
            "langgraph": langgraph,
            "install_exit": install.returncode,
        }
        if install.returncode == 0:
            execution = subprocess.run(
                [str(python), str(probe), str(args.output.resolve() / f"{label}.json")],
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
                env=clean,
            )
            row["probe_exit"] = execution.returncode
            (args.output / f"{label}-probe.log").write_text(
                execution.stdout + execution.stderr, encoding="utf-8"
            )
            frozen = subprocess.run(
                [args.uv, "pip", "freeze", "--python", str(python)],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            (args.output / f"{label}-requirements.txt").write_text(
                frozen.stdout, encoding="utf-8"
            )
        results.append(row)
        print(json.dumps(row), flush=True)
    unexpected = assess(results, args.output)
    (args.output / "assessment.json").write_text(
        json.dumps(
            {
                "unexpected": unexpected,
                "note": "Known migration failures remain recorded in raw probe reports.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (args.output / "matrix.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )

    if unexpected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

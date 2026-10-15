"""Execute the authored learning examples; validate snippets and record evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/learning/langchain_1_4_6"
DOCS = ROOT / "docs/learning/langchain-1.4.6"
CASES = (
    ("01_minimal_agent", "Reply: Hello, Sunny!\nMessages: 2\n"),
    ("02_middleware", "Hooks: before_model -> after_model\nReply: Observed reply\n"),
    (
        "03_conversation_state",
        (
            "Same conversation: 2 -> 4 messages\nSeparate conversation: 2 messages\n"
            "Missing thread configuration: rejected\n"
        ),
    ),
    (
        "04_tool_call",
        (
            "Executed tool: add(2, 3) = 5\n"
            "Message order: human -> ai -> tool -> ai\n"
            "Invalid integer argument: tool error; function not executed\n"
        ),
    ),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / ".site-work/learning-results.json"
    )
    args = parser.parse_args()
    pins = {}
    for line in (EXAMPLES / "requirements.txt").read_text().splitlines():
        name, expected = line.split("==")
        actual = version(name)
        if actual != expected:
            raise ValueError(f"Dependency mismatch: {name}: {actual} != {expected}")
        pins[name] = actual
    if sys.version_info[:2] != (3, 12):
        raise ValueError("Run these examples with Python 3.12")
    results = []
    environment = {
        **os.environ,
        "LANGCHAIN_TRACING_V2": "false",
        "LANGSMITH_TRACING": "false",
    }
    # Deny Python socket connections/DNS. This is an offline guard for these
    # trusted examples, not an OS sandbox for arbitrary third-party code.
    guard = (
        "import runpy,socket,sys\n"
        "def deny(*a,**k): raise RuntimeError('Network disabled for offline recipe')\n"
        "socket.socket.connect=deny\nsocket.create_connection=deny\n"
        "socket.getaddrinfo=deny\nrunpy.run_path(sys.argv[1],run_name='__main__')\n"
    )
    for name, expected in CASES:
        source = EXAMPLES / (name + ".py")
        page = DOCS / (name + ".md")
        snippet = page.read_text().split("```python\n", 1)[1].split("\n```", 1)[0]
        if snippet.strip() != source.read_text().strip():
            raise ValueError(f"Documentation snippet drift: {page.name}")
        run = subprocess.run(
            [sys.executable, "-c", guard, str(source)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
        )
        passed = run.returncode == 0 and run.stdout == expected
        results.append(
            {
                "example": source.relative_to(ROOT).as_posix(),
                "source_sha256": digest(source),
                "page_sha256": digest(page),
                "status": "passed" if passed else "failed",
                "stdout": run.stdout,
                "stderr": run.stderr,
                "returncode": run.returncode,
            }
        )
    report = {
        "executed_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "dependencies": pins,
        "requirements_sha256": digest(EXAMPLES / "requirements.txt"),
        "review_status": "author-written; final human content approval pending",
        "scope": "fixed-response models; local tool execution and invalid arguments tested; no provider inference/durable storage",
        "network": "Python socket connections and DNS denied; not a security sandbox",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for result in results:
        print(f"{result['status']}: {result['example']}")
    if any(result["status"] != "passed" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

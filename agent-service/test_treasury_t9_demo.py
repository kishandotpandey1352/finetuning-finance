from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def main():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_treasury_demo.py"), "--compact"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise AssertionError(
            f"run_treasury_demo.py exited with {proc.returncode}"
        )

    output = proc.stdout
    required = [
        "REMITLY TREASURY MULTI-AGENT DEMO",
        "SCENARIO: NORMAL",
        "SCENARIO: SHORTFALL",
        "SCENARIO: STALE",
        "SCENARIO: TOOL_FAILURE",
        "SCENARIO: UNAUTHORIZED_TOOL",
        "DEMO SUMMARY: 5/5 selected scenario(s) passed.",
        "Treasury demo completed successfully.",
    ]

    for marker in required:
        assert marker in output, f"Missing demo output marker: {marker}"

    print(
        "PASS: T9 packaged Treasury demo runs from one command and "
        "validates all five interview scenarios."
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import subprocess
import sys


def run_qg_runner(input_text: str, mode: str = "edit"):
    proc = subprocess.run(
        [sys.executable, "qualitygate/scripts/qg_runner.py", "--mode", mode, "--source", "stdin"],
        input=input_text,
        text=True,
        capture_output=True,
    )
    return proc


def test_qg_runner_blocks_critical_api_key():
    critical = "sk_test_1234567890abcdef1234567890abcdef"
    proc = run_qg_runner(critical, mode="edit")
    # Should block with rc=2
    assert proc.returncode == 2, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    assert data["status"] == "blocked"
    assert data["block"] is True
    assert data["severity"] == "CRITICAL"


def test_qg_runner_passes_safe_text():
    safe = "hello world"
    proc = run_qg_runner(safe, mode="edit")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    assert data["block"] is False
    assert data["status"] in ("passed", "passed_with_warnings", "no_content")


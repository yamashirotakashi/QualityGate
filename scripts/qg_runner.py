#!/usr/bin/env python3
"""
QualityGate Codex Runner (qg_runner)

Purpose:
- Safe, Codex-facing CLI to run QualityGate checks before edits or bash commands.
- Keeps Claude Code (CC) integration untouched while enabling Codex pre-checks.

Behavior:
- Reads content from stdin or file.
- Uses SeverityAnalyzer to classify findings.
- Exits with 2 on CRITICAL (block), 0 otherwise. Supports warn-only mode.

Usage examples:
  # Check edit content from stdin
  echo "sk_test_1234567890abcdef1234567890abcdef" | \
    python qualitygate/scripts/qg_runner.py --mode edit --source stdin

  # Check bash command
  echo "rm -rf /" | python qualitygate/scripts/qg_runner.py --mode bash --source stdin

Notes:
- Respects QUALITYGATE_ROOT if provided, otherwise resolves relative to this file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any


def resolve_qualitygate_root() -> Path:
    # 1) Explicit env
    env_root = os.environ.get("QUALITYGATE_ROOT")
    if env_root:
        p = Path(env_root)
        if p.exists():
            return p

    # 2) Relative to this script: qualitygate/
    return Path(__file__).resolve().parents[1]


def load_stdin(timeout_ms: int) -> str:
    # Best-effort read with soft timeout semantics (no actual alarm to keep portable)
    start = time.time()
    data = sys.stdin.read() if not sys.stdin.isatty() else ""
    # Soft timeout guard (elapsed check; no blocking behavior here)
    _ = timeout_ms  # reserved for future hard timeout if needed
    return data


@dataclass
class RunnerResult:
    status: str
    severity: Optional[str] = None
    message: Optional[str] = None
    pattern: Optional[str] = None
    block: bool = False

    def to_json(self) -> str:
        return json.dumps({
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "pattern": self.pattern,
            "block": self.block,
        }, ensure_ascii=False)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="QualityGate Codex Runner")
    parser.add_argument("--mode", choices=["edit", "bash"], required=True)
    parser.add_argument("--source", choices=["stdin", "file"], default="stdin")
    parser.add_argument("--file", help="Path to file when --source=file")
    parser.add_argument("--warn-only", action="store_true", help="Do not block on CRITICAL; print warning only")
    parser.add_argument("--timeout-ms", type=int, default=5000)
    parser.add_argument("--pretty", action="store_true", help="Pretty alert output with emojis to stderr")
    args = parser.parse_args(argv)

    # Resolve project root for analyzer
    qg_root = resolve_qualitygate_root()
    os.environ.setdefault("QUALITYGATE_ROOT", str(qg_root))

    # Import analyzer after path setup
    scripts_dir = qg_root / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from severity_analyzer import SeverityAnalyzer  # type: ignore
    except Exception as e:
        # Fail safe: do not block operations if analyzer import fails
        rr = RunnerResult(status="error", message=f"Analyzer import failed: {e}", block=False)
        print(rr.to_json())
        return 0

    # Load content
    if args.source == "stdin":
        content = load_stdin(args.timeout_ms)
    else:
        if not args.file:
            rr = RunnerResult(status="error", message="--file is required when --source=file", block=False)
            print(rr.to_json())
            return 0
        path = Path(args.file)
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            rr = RunnerResult(status="error", message=f"Failed to read file: {e}", block=False)
            print(rr.to_json())
            return 0

    if not content.strip():
        rr = RunnerResult(status="no_content", message="No content to analyze", block=False)
        print(rr.to_json())
        return 0

    try:
        analyzer = SeverityAnalyzer()
        finding: Optional[Dict[str, Any]] = analyzer.analyze(content)
        if not finding:
            rr = RunnerResult(status="passed", block=False)
            print(rr.to_json())
            # Optional pretty pass message
            pretty_env = os.environ.get("QG_PRETTY", "").lower() in ("1", "true", "yes")
            if args.pretty or pretty_env:
                print("✅ QualityGate: Passed", file=sys.stderr)
            return 0

        severity = str(finding.get("severity"))
        message = str(finding.get("message"))
        pattern = str(finding.get("pattern", ""))

        # Pretty alert output
        pretty_env = os.environ.get("QG_PRETTY", "").lower() in ("1", "true", "yes")
        if args.pretty or pretty_env:
            if severity.upper() == "CRITICAL":
                print("\n🛑🚨 QualityGate CRITICAL detected 🚨🛑", file=sys.stderr)
                print(f"• Detail: {message}", file=sys.stderr)
                if pattern:
                    print(f"• Pattern: {pattern}", file=sys.stderr)
                print("Action: Blocked. Please fix and re-run.", file=sys.stderr)
            elif severity.upper() == "HIGH":
                print("\n⚠️ QualityGate HIGH warning", file=sys.stderr)
                print(f"• Detail: {message}", file=sys.stderr)
                if pattern:
                    print(f"• Pattern: {pattern}", file=sys.stderr)
                print("Action: Allowed (warn). Review recommended.", file=sys.stderr)
            else:
                print("\nℹ️ QualityGate INFO", file=sys.stderr)
                print(f"• Detail: {message}", file=sys.stderr)
                if pattern:
                    print(f"• Pattern: {pattern}", file=sys.stderr)
        else:
            # Minimal human-readable detail
            print(f"QualityGate {severity}: {message}", file=sys.stderr)

        is_critical = (severity.upper() == "CRITICAL")
        if is_critical and not args.warn_only:
            rr = RunnerResult(status="blocked", severity=severity, message=message, pattern=pattern, block=True)
            print(rr.to_json())
            return 2

        # Warn-only or non-critical
        rr = RunnerResult(status="passed_with_warnings" if is_critical else "passed",
                          severity=severity, message=message, pattern=pattern, block=False)
        print(rr.to_json())
        return 0

    except Exception as e:
        # Fail safe: do not block on internal errors
        rr = RunnerResult(status="error", message=f"Analyzer error: {e}", block=False)
        print(rr.to_json())
        return 0


if __name__ == "__main__":
    sys.exit(main())

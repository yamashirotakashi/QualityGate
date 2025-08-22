#!/usr/bin/env python3
import json
import os
from unittest.mock import patch

from qualitygate.hooks.qualitygate_bridge import QualityGateBridge


def _make_event(tool: str, payload: str):
    if tool == "Edit":
        params = {"content": payload}
    else:
        params = {"command": payload}
    return {"tool": {"name": tool, "parameters": params}}


def test_bridge_injects_env_for_edit():
    captured = {}

    def fake_popen(cmd, stdin, stdout, stderr, text, cwd, env):  # signature subset
        captured["env"] = dict(env)

        class Proc:
            def communicate(self, input=None, timeout=None):
                return ("", "blocked")

            @property
            def returncode(self):
                return 2  # simulate CRITICAL block from hook

        return Proc()

    with patch("subprocess.Popen", fake_popen):
        bridge = QualityGateBridge()
        content = "sk_test_1234567890abcdef1234567890abcdef"
        result = bridge.process_event(_make_event("Edit", content))

    assert result["block"] is True
    assert captured["env"].get("CLAUDE_HOOK_MESSAGE") == content
    assert "CLAUDE_HOOK_COMMAND" not in captured["env"]
    assert "QUALITYGATE_ROOT" in captured["env"]


def test_bridge_injects_env_for_bash():
    captured = {}

    def fake_popen(cmd, stdin, stdout, stderr, text, cwd, env):
        captured["env"] = dict(env)

        class Proc:
            def communicate(self, input=None, timeout=None):
                return ("ok", "")

            @property
            def returncode(self):
                return 0

        return Proc()

    with patch("subprocess.Popen", fake_popen):
        bridge = QualityGateBridge()
        command = "echo hello"
        result = bridge.process_event(_make_event("Bash", command))

    assert result["block"] is False
    assert captured["env"].get("CLAUDE_HOOK_COMMAND") == command
    assert "QUALITYGATE_ROOT" in captured["env"]


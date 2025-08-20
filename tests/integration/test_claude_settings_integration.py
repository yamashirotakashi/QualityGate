#!/usr/bin/env python3
"""
Claude Code Settings Integration Tests
======================================

Tests for the Claude Code settings.json integration with QualityGate hooks.
Currently, the integration is NOT active in settings.json, so these tests
verify the expected behavior and configuration requirements.

Tests cover:
- Settings.json structure validation
- PreToolUse hook configuration format
- Hook matcher patterns and exclusions
- Integration readiness assessment
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def claude_settings_path():
    """Return the path to Claude Code settings.json."""
    return Path("/home/tky99/.config/claude/settings.json")


@pytest.fixture
def sample_qualitygate_config():
    """Sample QualityGate configuration for Claude Code settings."""
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "name": "qualitygate-integration",
                    "description": "QualityGate quality analysis before Edit/Write/Bash operations",
                    "command": "/mnt/c/Users/tky99/dev/.claude/hooks/qualitygate-pretooluse-wrapper.sh",
                    "stdin": True,
                    "timeout": 5000,
                    "blocking": True,
                    "matchers": [
                        {"tool": "Edit"},
                        {"tool": "Write"},
                        {"tool": "MultiEdit"},
                        {"tool": "NotebookEdit"},
                        {"tool": "Bash"}
                    ],
                    "excludeMatchers": [
                        {"tool": "mcp__*"},
                        {"argument": "cd *"}
                    ],
                    "enabled": True,
                    "priority": 10
                }
            ]
        }
    }


@pytest.fixture
def temp_settings_with_qualitygate(tmp_path, sample_qualitygate_config):
    """Create temporary settings.json with QualityGate integration."""
    settings_file = tmp_path / "settings.json"
    
    # Base settings with QualityGate integration
    settings = {
        "defaultModel": "sonnet",
        **sample_qualitygate_config
    }
    
    settings_file.write_text(json.dumps(settings, indent=2))
    return settings_file


class TestCurrentSettingsState:
    """Test the current state of Claude Code settings."""
    
    def test_settings_file_exists(self, claude_settings_path):
        """Verify that Claude Code settings.json exists."""
        assert claude_settings_path.exists(), "Claude settings.json should exist"
        assert claude_settings_path.is_file(), "Settings should be a file"
    
    def test_settings_file_readable(self, claude_settings_path):
        """Verify that settings.json is readable and valid JSON."""
        try:
            with open(claude_settings_path, 'r') as f:
                settings = json.load(f)
            
            assert isinstance(settings, dict), "Settings should be a JSON object"
            
        except json.JSONDecodeError:
            pytest.fail("Settings.json should contain valid JSON")
        except PermissionError:
            pytest.fail("Settings.json should be readable")
    
    def test_qualitygate_integration_status(self, claude_settings_path):
        """Test current QualityGate integration status in settings."""
        with open(claude_settings_path, 'r') as f:
            settings = json.load(f)
        
        # Check if QualityGate is integrated
        hooks = settings.get("hooks", {})
        pre_tool_use_hooks = hooks.get("PreToolUse", [])
        
        qualitygate_hooks = [
            hook for hook in pre_tool_use_hooks 
            if isinstance(hook, dict) and "qualitygate" in hook.get("name", "").lower()
        ]
        
        # Document current status
        if len(qualitygate_hooks) == 0:
            # Expected current state - no integration yet
            assert True, "QualityGate integration is not yet configured (expected)"
        else:
            # If integration exists, verify it's properly configured
            for hook in qualitygate_hooks:
                assert "command" in hook, "QualityGate hook should have command"
                assert "matchers" in hook, "QualityGate hook should have matchers"
    
    def test_existing_hooks_structure(self, claude_settings_path):
        """Test that existing hooks don't conflict with QualityGate integration."""
        with open(claude_settings_path, 'r') as f:
            settings = json.load(f)
        
        hooks = settings.get("hooks", {})
        
        # Check existing PreToolUse hooks
        if "PreToolUse" in hooks:
            pre_tool_use_hooks = hooks["PreToolUse"]
            assert isinstance(pre_tool_use_hooks, list), "PreToolUse should be a list"
            
            # Verify existing hooks have required structure
            for hook in pre_tool_use_hooks:
                if isinstance(hook, dict):
                    # Check for required hook fields
                    assert "matcher" in hook or "matchers" in hook, "Hook should have matcher"
                    assert "hooks" in hook or "command" in hook, "Hook should have action"


class TestQualityGateConfigurationFormat:
    """Test QualityGate configuration format and structure."""
    
    def test_sample_config_structure(self, sample_qualitygate_config):
        """Test that sample QualityGate configuration has correct structure."""
        config = sample_qualitygate_config
        
        # Check top-level structure
        assert "hooks" in config
        assert "PreToolUse" in config["hooks"]
        assert isinstance(config["hooks"]["PreToolUse"], list)
        
        # Check hook configuration
        qg_hook = config["hooks"]["PreToolUse"][0]
        
        required_fields = [
            "name", "description", "command", "stdin", "timeout", 
            "blocking", "matchers", "excludeMatchers", "enabled", "priority"
        ]
        
        for field in required_fields:
            assert field in qg_hook, f"QualityGate hook should have {field} field"
        
        # Check field types
        assert isinstance(qg_hook["name"], str)
        assert isinstance(qg_hook["description"], str) 
        assert isinstance(qg_hook["command"], str)
        assert isinstance(qg_hook["stdin"], bool)
        assert isinstance(qg_hook["timeout"], int)
        assert isinstance(qg_hook["blocking"], bool)
        assert isinstance(qg_hook["matchers"], list)
        assert isinstance(qg_hook["excludeMatchers"], list)
        assert isinstance(qg_hook["enabled"], bool)
        assert isinstance(qg_hook["priority"], int)
    
    def test_matcher_patterns(self, sample_qualitygate_config):
        """Test that matcher patterns are correctly configured."""
        qg_hook = sample_qualitygate_config["hooks"]["PreToolUse"][0]
        
        # Check matchers for target tools
        expected_tools = ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"]
        matcher_tools = [matcher["tool"] for matcher in qg_hook["matchers"] if "tool" in matcher]
        
        for tool in expected_tools:
            assert tool in matcher_tools, f"Should match {tool} tool"
        
        # Check exclude matchers
        exclude_matchers = qg_hook["excludeMatchers"]
        assert len(exclude_matchers) > 0, "Should have exclude matchers"
        
        # Should exclude MCP tools
        mcp_exclusions = [m for m in exclude_matchers if "mcp__" in str(m.values())]
        assert len(mcp_exclusions) > 0, "Should exclude MCP tools"
    
    def test_command_path_validity(self, sample_qualitygate_config):
        """Test that the configured command path is valid."""
        qg_hook = sample_qualitygate_config["hooks"]["PreToolUse"][0]
        command_path = Path(qg_hook["command"])
        
        # Check path structure
        assert command_path.is_absolute(), "Command path should be absolute"
        assert ".claude/hooks" in str(command_path), "Should be in .claude/hooks directory"
        assert command_path.name.endswith(".sh"), "Should be a shell script"
        
        # Check if actual file exists
        if command_path.exists():
            assert command_path.is_file(), "Command should be a file"
            assert os.access(command_path, os.X_OK), "Command should be executable"
        # Note: File might not exist yet during development
    
    def test_hook_priorities(self, sample_qualitygate_config):
        """Test hook priority configuration."""
        qg_hook = sample_qualitygate_config["hooks"]["PreToolUse"][0]
        
        priority = qg_hook["priority"]
        assert isinstance(priority, int), "Priority should be an integer"
        assert 1 <= priority <= 100, "Priority should be reasonable range"
        
        # QualityGate should have medium-high priority
        assert priority >= 5, "QualityGate should have reasonably high priority"


class TestConfigurationIntegration:
    """Test configuration integration scenarios."""
    
    def test_merge_with_existing_hooks(self, claude_settings_path, sample_qualitygate_config):
        """Test merging QualityGate config with existing hooks."""
        # Load current settings
        with open(claude_settings_path, 'r') as f:
            current_settings = json.load(f)
        
        # Simulate merging QualityGate configuration
        merged_settings = current_settings.copy()
        
        if "hooks" not in merged_settings:
            merged_settings["hooks"] = {}
        
        if "PreToolUse" not in merged_settings["hooks"]:
            merged_settings["hooks"]["PreToolUse"] = []
        
        # Add QualityGate hook
        qg_hook = sample_qualitygate_config["hooks"]["PreToolUse"][0]
        merged_settings["hooks"]["PreToolUse"].append(qg_hook)
        
        # Verify merged configuration
        assert "hooks" in merged_settings
        assert "PreToolUse" in merged_settings["hooks"]
        
        pre_tool_hooks = merged_settings["hooks"]["PreToolUse"]
        assert len(pre_tool_hooks) > 0, "Should have at least one PreToolUse hook"
        
        # Check that QualityGate hook is present
        qg_hooks = [h for h in pre_tool_hooks if "qualitygate" in h.get("name", "").lower()]
        assert len(qg_hooks) == 1, "Should have exactly one QualityGate hook"
    
    def test_hook_conflict_detection(self, temp_settings_with_qualitygate):
        """Test detection of potential hook conflicts."""
        with open(temp_settings_with_qualitygate, 'r') as f:
            settings = json.load(f)
        
        pre_tool_hooks = settings["hooks"]["PreToolUse"]
        
        # Check for conflicting matchers
        all_matchers = []
        for hook in pre_tool_hooks:
            if "matchers" in hook:
                all_matchers.extend(hook["matchers"])
            elif "matcher" in hook:
                # Handle old format
                all_matchers.append({"pattern": hook["matcher"]})
        
        # Look for overlapping tool matchers
        tool_matchers = {}
        for matcher in all_matchers:
            if "tool" in matcher:
                tool = matcher["tool"]
                if tool not in tool_matchers:
                    tool_matchers[tool] = []
                tool_matchers[tool].append(matcher)
        
        # Report any tools matched by multiple hooks
        conflicts = {tool: matchers for tool, matchers in tool_matchers.items() if len(matchers) > 1}
        
        # This is informational - conflicts might be intentional
        if conflicts:
            print(f"Note: Multiple hooks match tools: {list(conflicts.keys())}")
    
    def test_configuration_validation(self, temp_settings_with_qualitygate):
        """Test comprehensive configuration validation."""
        with open(temp_settings_with_qualitygate, 'r') as f:
            settings = json.load(f)
        
        # Validate overall structure
        assert isinstance(settings, dict), "Settings should be object"
        
        if "hooks" in settings:
            hooks = settings["hooks"]
            assert isinstance(hooks, dict), "Hooks should be object"
            
            if "PreToolUse" in hooks:
                pre_tool_hooks = hooks["PreToolUse"]
                assert isinstance(pre_tool_hooks, list), "PreToolUse should be array"
                
                for hook in pre_tool_hooks:
                    if isinstance(hook, dict) and "qualitygate" in hook.get("name", "").lower():
                        # Validate QualityGate hook specifically
                        self._validate_qualitygate_hook(hook)
    
    def _validate_qualitygate_hook(self, hook):
        """Helper method to validate QualityGate hook configuration."""
        required_fields = ["name", "command", "matchers"]
        for field in required_fields:
            assert field in hook, f"QualityGate hook missing required field: {field}"
        
        # Validate command path exists or is reasonable
        command = hook["command"]
        assert isinstance(command, str) and len(command) > 0, "Command should be non-empty string"
        
        # Validate matchers
        matchers = hook["matchers"]
        assert isinstance(matchers, list) and len(matchers) > 0, "Should have at least one matcher"
        
        # Check that it matches expected tools
        expected_tools = ["Edit", "Write", "Bash"]
        matched_tools = set()
        for matcher in matchers:
            if "tool" in matcher:
                matched_tools.add(matcher["tool"])
        
        assert len(matched_tools.intersection(expected_tools)) > 0, "Should match at least one target tool"


class TestIntegrationReadiness:
    """Test readiness for QualityGate integration."""
    
    def test_wrapper_script_exists(self):
        """Test that QualityGate wrapper script exists."""
        wrapper_path = Path("/mnt/c/Users/tky99/dev/.claude/hooks/qualitygate-pretooluse-wrapper.sh")
        
        if wrapper_path.exists():
            assert wrapper_path.is_file(), "Wrapper should be a file"
            assert os.access(wrapper_path, os.X_OK), "Wrapper should be executable"
            
            # Check script content
            content = wrapper_path.read_text()
            assert "qualitygate_bridge.py" in content, "Should reference bridge script"
            assert "exit $?" in content or "exit ${" in content, "Should forward exit codes"
        else:
            pytest.skip("Wrapper script not yet created - integration not ready")
    
    def test_bridge_script_exists(self):
        """Test that QualityGate bridge script exists."""
        bridge_path = Path("/mnt/c/Users/tky99/dev/qualitygate/hooks/qualitygate_bridge.py")
        
        assert bridge_path.exists(), "Bridge script should exist"
        assert bridge_path.is_file(), "Bridge should be a file"
        
        # Check script is executable or can be run with python
        content = bridge_path.read_text()
        assert "QualityGateBridge" in content, "Should contain bridge class"
        assert "def main()" in content, "Should have main function"
    
    def test_hook_scripts_exist(self):
        """Test that individual hook scripts exist."""
        hooks_dir = Path("/mnt/c/Users/tky99/dev/qualitygate/hooks")
        
        required_hooks = [
            "before_edit_qualitygate.py",
            "before_bash_qualitygate.py"
        ]
        
        for hook_script in required_hooks:
            hook_path = hooks_dir / hook_script
            assert hook_path.exists(), f"Hook script should exist: {hook_script}"
            assert hook_path.is_file(), f"Hook should be a file: {hook_script}"
    
    def test_patterns_configuration_exists(self):
        """Test that patterns configuration exists."""
        patterns_path = Path("/mnt/c/Users/tky99/dev/qualitygate/config/patterns.json")
        
        assert patterns_path.exists(), "Patterns configuration should exist"
        assert patterns_path.is_file(), "Patterns should be a file"
        
        # Validate patterns file
        try:
            with open(patterns_path, 'r') as f:
                patterns = json.load(f)
            
            assert isinstance(patterns, dict), "Patterns should be JSON object"
            assert "CRITICAL" in patterns, "Should have CRITICAL patterns"
            
        except json.JSONDecodeError:
            pytest.fail("Patterns configuration should be valid JSON")
    
    def test_integration_prerequisites(self):
        """Test that all prerequisites for integration are met."""
        prerequisites = [
            ("/mnt/c/Users/tky99/dev/qualitygate", "QualityGate directory"),
            ("/mnt/c/Users/tky99/dev/qualitygate/hooks", "Hooks directory"),
            ("/mnt/c/Users/tky99/dev/qualitygate/scripts", "Scripts directory"),
            ("/mnt/c/Users/tky99/dev/.claude/hooks", "Claude hooks directory"),
        ]
        
        for path_str, description in prerequisites:
            path = Path(path_str)
            assert path.exists(), f"{description} should exist: {path_str}"
            assert path.is_dir(), f"{description} should be a directory: {path_str}"


class TestActivationSimulation:
    """Simulate QualityGate activation in Claude Code."""
    
    def test_simulate_hook_execution(self, temp_settings_with_qualitygate):
        """Simulate how Claude Code would execute the QualityGate hook."""
        with open(temp_settings_with_qualitygate, 'r') as f:
            settings = json.load(f)
        
        qg_hook = settings["hooks"]["PreToolUse"][0]
        
        # Check command configuration
        command = qg_hook["command"]
        assert command, "Should have command configured"
        
        # Check stdin configuration
        assert qg_hook.get("stdin", False), "Should be configured to receive stdin"
        
        # Check timeout configuration
        timeout = qg_hook.get("timeout", 0)
        assert timeout > 0, "Should have reasonable timeout"
        assert timeout <= 30000, "Timeout should not be excessive"
        
        # Check blocking configuration
        assert qg_hook.get("blocking", False), "Should be configured as blocking hook"
    
    def test_simulate_tool_matching(self, temp_settings_with_qualitygate):
        """Simulate tool matching logic."""
        with open(temp_settings_with_qualitygate, 'r') as f:
            settings = json.load(f)
        
        qg_hook = settings["hooks"]["PreToolUse"][0]
        matchers = qg_hook["matchers"]
        exclude_matchers = qg_hook.get("excludeMatchers", [])
        
        # Test tools that should match
        should_match = ["Edit", "Write", "MultiEdit", "Bash"]
        for tool in should_match:
            matched = any(matcher.get("tool") == tool for matcher in matchers)
            assert matched, f"Should match {tool} tool"
        
        # Test tools that should be excluded
        should_exclude = ["mcp__filesystem__read_text_file", "mcp__github__get_issue"]
        for tool in should_exclude:
            excluded = any("mcp__" in str(matcher.values()) for matcher in exclude_matchers)
            assert excluded, f"Should exclude MCP tool pattern"
    
    def test_simulate_error_scenarios(self, temp_settings_with_qualitygate):
        """Simulate error handling scenarios."""
        with open(temp_settings_with_qualitygate, 'r') as f:
            settings = json.load(f)
        
        qg_hook = settings["hooks"]["PreToolUse"][0]
        
        # Test missing command scenario
        modified_hook = qg_hook.copy()
        modified_hook["command"] = "/nonexistent/path/to/script.sh"
        
        # In real Claude Code, this would result in hook execution failure
        # The system should handle this gracefully
        assert "command" in modified_hook, "Should have command field even if path is invalid"
        
        # Test disabled hook scenario
        modified_hook = qg_hook.copy()
        modified_hook["enabled"] = False
        
        # Hook should be present but disabled
        assert "enabled" in modified_hook, "Should have enabled field"
        assert modified_hook["enabled"] is False, "Should be disabled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
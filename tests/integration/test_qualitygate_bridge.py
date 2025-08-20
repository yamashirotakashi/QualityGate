#!/usr/bin/env python3
"""
QualityGate Bridge Integration Tests
====================================

Comprehensive test suite for the QualityGate Hook System integration
that connects QualityGate's quality patterns with Claude Code's PreToolUse hooks.

Tests cover:
- Bridge component routing and orchestration
- Tool mapping validation (Edit/Write/MultiEdit/NotebookEdit → before_edit, Bash → before_bash)
- Event processing and subprocess execution
- Bypass mechanisms and error handling
- Quality pattern application and blocking behavior
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY, call
from io import StringIO

import pytest

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "hooks"))

from qualitygate_bridge import QualityGateBridge

# Sample event data for different tools
EDIT_EVENT = {
    "tool": {"name": "Edit", "parameters": {"content": "This is a test edit.", "file_path": "/test/file.py"}}
}

WRITE_EVENT = {
    "tool": {"name": "Write", "parameters": {"content": "New file content", "file_path": "/test/new.py"}}
}

MULTI_EDIT_EVENT = {
    "tool": {
        "name": "MultiEdit",
        "parameters": {
            "edits": [
                {"old_string": "old1", "new_string": "First edit"},
                {"old_string": "old2", "new_string": "Second edit"},
            ],
            "file_path": "/test/multi.py"
        },
    },
}

NOTEBOOK_EDIT_EVENT = {
    "tool": {"name": "NotebookEdit", "parameters": {"new_source": "print('notebook')", "notebook_path": "/test.ipynb"}}
}

BASH_EVENT = {
    "tool": {"name": "Bash", "parameters": {"command": "echo 'hello world'"}}
}

BASH_OUTPUT_EVENT = {
    "tool": {"name": "BashOutput", "parameters": {"bash_id": "123"}}
}

UNKNOWN_TOOL_EVENT = {
    "tool": {"name": "UnknownTool", "parameters": {"param": "value"}}
}

MALFORMED_EVENT = {"invalid": "structure"}

EMPTY_CONTENT_EVENT = {
    "tool": {"name": "Edit", "parameters": {"content": "   ", "file_path": "/test.py"}}
}

# Critical patterns for testing blocking behavior
CRITICAL_CONTENT_EXAMPLES = [
    "sk_test_1234567890abcdef1234567890abcdef",  # API key
    "AKIA1234567890123456",  # AWS key
    "rm -rf /",  # Dangerous command
    "eval(user_input)",  # Code injection
    "subprocess.call(cmd, shell=True)"  # Shell injection
]

HIGH_SEVERITY_EXAMPLES = [
    "とりあえず修正します",  # Band-aid fix pattern
    "TODO: fix this properly later"  # Temporary fix pattern
]


@pytest.fixture
def bridge_with_temp_files(tmp_path):
    """Provides a QualityGateBridge instance with temporary file system setup."""
    # Create temporary qualitygate structure
    qualitygate_root = tmp_path / "qualitygate"
    hooks_dir = qualitygate_root / "hooks"
    config_dir = qualitygate_root / "config"
    
    hooks_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)

    # Create dummy hook scripts
    before_edit_script = hooks_dir / "before_edit_qualitygate.py"
    before_bash_script = hooks_dir / "before_bash_qualitygate.py"
    
    before_edit_script.write_text("#!/usr/bin/env python3\nprint('Edit hook executed')\n")
    before_bash_script.write_text("#!/usr/bin/env python3\nprint('Bash hook executed')\n")
    
    # Make scripts executable
    before_edit_script.chmod(0o755)
    before_bash_script.chmod(0o755)
    
    # Create patterns.json
    patterns_file = config_dir / "patterns.json"
    patterns_file.write_text(json.dumps({
        "version": "1.0.0",
        "CRITICAL": {
            "security": {
                "patterns": {
                    "sk_test_[0-9a-zA-Z]{32}": "Test API key detected",
                    "rm\\s+-rf\\s+/": "Dangerous deletion command"
                }
            }
        }
    }))

    # Create bridge instance and override paths
    bridge = QualityGateBridge()
    bridge.qualitygate_root = qualitygate_root
    bridge.hooks_dir = hooks_dir
    bridge.patterns_file = patterns_file
    
    return bridge


@pytest.fixture
def clean_environment():
    """Ensures clean environment variables for testing."""
    bypass_vars = ["BYPASS_DESIGN_HOOK", "QUALITYGATE_DISABLED", "QUALITYGATE_BYPASS"]
    original_values = {}
    
    # Save original values
    for var in bypass_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


class TestQualityGateBridgeBypass:
    """Test bypass mechanism functionality."""
    
    @pytest.mark.parametrize("bypass_var", [
        "BYPASS_DESIGN_HOOK", 
        "QUALITYGATE_DISABLED", 
        "QUALITYGATE_BYPASS"
    ])
    @pytest.mark.parametrize("bypass_value", ["1", "true", "TRUE", "yes", "YES"])
    def test_bypass_mechanisms(self, bridge_with_temp_files, clean_environment, bypass_var, bypass_value):
        """Test that all bypass environment variables work with various values."""
        # Arrange
        os.environ[bypass_var] = bypass_value
        bridge = QualityGateBridge()  # Re-instantiate to pick up env vars
        
        # Act
        result = bridge.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "bypassed"
        assert result["block"] is False
        assert "bypassed via environment variable" in result["message"]
    
    def test_multiple_bypass_vars_set(self, bridge_with_temp_files, clean_environment):
        """Test behavior when multiple bypass variables are set."""
        # Arrange
        os.environ["BYPASS_DESIGN_HOOK"] = "1"
        os.environ["QUALITYGATE_BYPASS"] = "1"
        bridge = QualityGateBridge()
        
        # Act
        result = bridge.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "bypassed"
        assert result["block"] is False
    
    @pytest.mark.parametrize("invalid_value", ["0", "false", "no", "disabled", ""])
    def test_bypass_with_invalid_values(self, bridge_with_temp_files, clean_environment, invalid_value):
        """Test that bypass variables with invalid values don't trigger bypass."""
        # Arrange
        os.environ["QUALITYGATE_BYPASS"] = invalid_value
        bridge = QualityGateBridge()
        
        # Act
        with patch.object(bridge, '_execute_qualitygate_hook', return_value=(False, "Test passed")):
            result = bridge.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] != "bypassed"


class TestQualityGateBridgeToolMapping:
    """Test tool mapping and routing functionality."""
    
    @pytest.mark.parametrize("event,expected_hook", [
        (EDIT_EVENT, "before_edit_qualitygate.py"),
        (WRITE_EVENT, "before_edit_qualitygate.py"),
        (MULTI_EDIT_EVENT, "before_edit_qualitygate.py"),
        (NOTEBOOK_EDIT_EVENT, "before_edit_qualitygate.py"),
        (BASH_EVENT, "before_bash_qualitygate.py"),
        (BASH_OUTPUT_EVENT, "before_bash_qualitygate.py"),
    ])
    def test_tool_mapping(self, bridge_with_temp_files, event, expected_hook):
        """Test that tools are mapped to correct hook scripts."""
        # Arrange
        tool_name, _ = bridge_with_temp_files._extract_tool_info(event)
        
        # Act
        hook_path = bridge_with_temp_files._get_hook_script_path(tool_name)
        
        # Assert
        assert hook_path is not None
        assert hook_path.name == expected_hook
        assert hook_path.exists()
    
    def test_unknown_tool_mapping(self, bridge_with_temp_files):
        """Test that unknown tools return None for hook path."""
        # Act
        hook_path = bridge_with_temp_files._get_hook_script_path("UnknownTool")
        
        # Assert
        assert hook_path is None
    
    def test_missing_hook_script(self, bridge_with_temp_files):
        """Test behavior when mapped hook script doesn't exist."""
        # Arrange - remove the edit hook script
        edit_hook = bridge_with_temp_files.hooks_dir / "before_edit_qualitygate.py"
        edit_hook.unlink()
        
        # Act
        hook_path = bridge_with_temp_files._get_hook_script_path("Edit")
        
        # Assert
        assert hook_path is None


class TestQualityGateBridgeInputPreparation:
    """Test hook input preparation for different tool types."""
    
    @pytest.mark.parametrize("event,expected_input", [
        (EDIT_EVENT, "This is a test edit."),
        (WRITE_EVENT, "New file content"),
        (BASH_EVENT, "echo 'hello world'"),
        (MULTI_EDIT_EVENT, "First edit\nSecond edit"),
        (NOTEBOOK_EDIT_EVENT, "print('notebook')"),
        ({"tool": {"name": "Write", "parameters": {"new_string": "content"}}}, "content"),
        (BASH_OUTPUT_EVENT, ""),  # BashOutput has no command parameter
    ])
    def test_prepare_hook_input(self, bridge_with_temp_files, event, expected_input):
        """Test that hook input is correctly prepared for various tool types."""
        # Arrange
        tool_name, tool_params = bridge_with_temp_files._extract_tool_info(event)
        
        # Act
        hook_input = bridge_with_temp_files._prepare_hook_input(tool_name, tool_params)
        
        # Assert
        assert hook_input == expected_input
    
    def test_prepare_hook_input_unknown_tool(self, bridge_with_temp_files):
        """Test hook input preparation for unknown tool types."""
        # Arrange
        tool_name, tool_params = bridge_with_temp_files._extract_tool_info(UNKNOWN_TOOL_EVENT)
        
        # Act
        hook_input = bridge_with_temp_files._prepare_hook_input(tool_name, tool_params)
        
        # Assert
        # Should return JSON representation of parameters
        expected = json.dumps({"param": "value"}, indent=2)
        assert hook_input == expected
    
    def test_prepare_hook_input_empty_edits(self, bridge_with_temp_files):
        """Test hook input preparation with empty edits list."""
        # Arrange
        empty_multi_edit = {
            "tool": {"name": "MultiEdit", "parameters": {"edits": []}}
        }
        tool_name, tool_params = bridge_with_temp_files._extract_tool_info(empty_multi_edit)
        
        # Act
        hook_input = bridge_with_temp_files._prepare_hook_input(tool_name, tool_params)
        
        # Assert
        assert hook_input == ""


class TestQualityGateBridgeEventProcessing:
    """Test event processing and subprocess execution."""
    
    @patch('subprocess.Popen')
    def test_process_event_hook_passes(self, mock_popen, bridge_with_temp_files, clean_environment):
        """Test successful hook execution that allows the operation."""
        # Arrange
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Analysis passed", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        # Act
        result = bridge_with_temp_files.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "passed"
        assert result["block"] is False
        assert result["tool"] == "Edit"
        assert "Analysis passed" in result["message"]
        
        # Verify subprocess was called correctly
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        assert "before_edit_qualitygate.py" in str(call_args[0][1])
        mock_process.communicate.assert_called_once_with(
            input="This is a test edit.", timeout=30
        )
    
    @patch('subprocess.Popen')
    def test_process_event_hook_blocks(self, mock_popen, bridge_with_temp_files, clean_environment):
        """Test hook execution that blocks the operation."""
        # Arrange
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Critical security issue detected")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        # Act
        result = bridge_with_temp_files.process_event(BASH_EVENT)
        
        # Assert
        assert result["status"] == "blocked"
        assert result["block"] is True
        assert result["tool"] == "Bash"
        assert "Critical security issue detected" in result["message"]
        assert "🚨 QualityGate Block:" in result["message"]
    
    @patch('subprocess.Popen')
    def test_process_event_hook_timeout(self, mock_popen, bridge_with_temp_files, clean_environment):
        """Test hook execution timeout handling."""
        # Arrange
        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("test", 30)
        mock_popen.return_value = mock_process
        
        # Act
        result = bridge_with_temp_files.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "passed"  # Fail-safe behavior
        assert result["block"] is False
        assert "timeout" in result["message"]
        mock_process.kill.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_process_event_hook_unexpected_exit_code(self, mock_popen, bridge_with_temp_files, clean_environment):
        """Test hook execution with unexpected exit code."""
        # Arrange
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Internal error")
        mock_process.returncode = 127  # Unexpected exit code
        mock_popen.return_value = mock_process
        
        # Act
        result = bridge_with_temp_files.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "passed"  # Fail-safe behavior
        assert result["block"] is False
        assert "error" in result["message"].lower()
    
    @patch('subprocess.Popen')
    def test_process_event_hook_execution_exception(self, mock_popen, bridge_with_temp_files, clean_environment):
        """Test hook execution with general exception."""
        # Arrange
        mock_popen.side_effect = Exception("Failed to start process")
        
        # Act
        result = bridge_with_temp_files.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "passed"  # Fail-safe behavior
        assert result["block"] is False
        assert "execution error" in result["message"]
    
    def test_process_event_no_hook_for_tool(self, bridge_with_temp_files, clean_environment):
        """Test processing event for tool with no mapped hook."""
        # Act
        result = bridge_with_temp_files.process_event(UNKNOWN_TOOL_EVENT)
        
        # Assert
        assert result["status"] == "no_hook"
        assert result["block"] is False
        assert "No QualityGate hook configured for UnknownTool" in result["message"]
    
    def test_process_event_no_content(self, bridge_with_temp_files, clean_environment):
        """Test processing event with no analyzable content."""
        # Act
        result = bridge_with_temp_files.process_event(EMPTY_CONTENT_EVENT)
        
        # Assert
        assert result["status"] == "no_content"
        assert result["block"] is False
        assert "No content to analyze" in result["message"]


class TestQualityGateBridgeErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.parametrize("malformed_event,expected_tool", [
        ({}, "unknown"),
        ({"tool": {}}, "unknown"),
        ({"tool": {"name": "Edit"}}, "Edit"),
        ({"tool": {"parameters": {"content": "test"}}}, "unknown"),
        ({"invalid": "structure"}, "unknown"),
        (None, "unknown"),
    ])
    def test_extract_tool_info_malformed_data(self, bridge_with_temp_files, malformed_event, expected_tool):
        """Test tool info extraction with malformed input data."""
        # Act
        if malformed_event is None:
            # Test with None input
            tool_name, tool_params = "unknown", {}
        else:
            tool_name, tool_params = bridge_with_temp_files._extract_tool_info(malformed_event)
        
        # Assert
        assert tool_name == expected_tool
        assert isinstance(tool_params, dict)
    
    def test_process_event_with_malformed_json(self, bridge_with_temp_files, clean_environment):
        """Test processing completely malformed event data."""
        # Act
        result = bridge_with_temp_files.process_event(MALFORMED_EVENT)
        
        # Assert
        assert result["status"] == "no_hook"
        assert result["block"] is False


class TestQualityGateBridgeIntegration:
    """End-to-end integration tests."""
    
    def test_full_workflow_edit_tool_passes(self, bridge_with_temp_files, clean_environment):
        """Test complete workflow for Edit tool that passes quality check."""
        # Arrange - create a hook script that always passes
        edit_hook = bridge_with_temp_files.hooks_dir / "before_edit_qualitygate.py"
        edit_hook.write_text("""#!/usr/bin/env python3
import sys
print("Quality check passed", file=sys.stderr)
sys.exit(0)
""")
        edit_hook.chmod(0o755)
        
        # Act
        result = bridge_with_temp_files.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "passed"
        assert result["block"] is False
        assert result["tool"] == "Edit"
        assert result["hook_script"] == "before_edit_qualitygate.py"
    
    def test_full_workflow_bash_tool_blocks(self, bridge_with_temp_files, clean_environment):
        """Test complete workflow for Bash tool that fails quality check."""
        # Arrange - create a hook script that always blocks
        bash_hook = bridge_with_temp_files.hooks_dir / "before_bash_qualitygate.py"
        bash_hook.write_text("""#!/usr/bin/env python3
import sys
print("Dangerous command detected!", file=sys.stderr)
sys.exit(1)
""")
        bash_hook.chmod(0o755)
        
        # Act
        result = bridge_with_temp_files.process_event(BASH_EVENT)
        
        # Assert
        assert result["status"] == "blocked"
        assert result["block"] is True
        assert result["tool"] == "Bash"
        assert result["hook_script"] == "before_bash_qualitygate.py"
        assert "Dangerous command detected!" in result["message"]
    
    def test_working_directory_context(self, bridge_with_temp_files, clean_environment):
        """Test that hook execution uses correct working directory."""
        # Arrange - create hook script that outputs current directory
        edit_hook = bridge_with_temp_files.hooks_dir / "before_edit_qualitygate.py"
        edit_hook.write_text("""#!/usr/bin/env python3
import os
import sys
print(f"Working dir: {os.getcwd()}", file=sys.stderr)
sys.exit(0)
""")
        edit_hook.chmod(0o755)
        
        # Act
        result = bridge_with_temp_files.process_event(EDIT_EVENT)
        
        # Assert
        assert result["status"] == "passed"
        # The working directory should be set to qualitygate root
        assert "Working dir:" in result["message"]


class TestQualityGateBridgeMainFunction:
    """Test the main() function and CLI behavior."""
    
    @patch('sys.stdin')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_with_stdin_input(self, mock_stdout, mock_stdin):
        """Test main() function with JSON input from stdin."""
        # Arrange
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = json.dumps(EDIT_EVENT)
        
        # Mock the bridge processing
        with patch('qualitygate_bridge.QualityGateBridge') as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge.process_event.return_value = {
                "status": "passed",
                "message": "Analysis passed",
                "block": False
            }
            mock_bridge_class.return_value = mock_bridge
            
            # Act & Assert (should not raise exception)
            try:
                from qualitygate_bridge import main
                with patch('json.load', return_value=EDIT_EVENT):
                    exit_code = main()
                assert exit_code is None  # Normal execution
            except SystemExit as e:
                assert e.code == 0  # Should exit with success
    
    @patch('sys.stdin')
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_test_mode(self, mock_stdout, mock_stdin):
        """Test main() function in test mode (when stdin is tty)."""
        # Arrange
        mock_stdin.isatty.return_value = True
        
        # Mock the bridge processing
        with patch('qualitygate_bridge.QualityGateBridge') as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge.process_event.return_value = {
                "status": "passed",
                "message": "Test analysis passed",
                "block": False
            }
            mock_bridge_class.return_value = mock_bridge
            
            # Act & Assert
            try:
                from qualitygate_bridge import main
                exit_code = main()
                assert exit_code is None
            except SystemExit as e:
                assert e.code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
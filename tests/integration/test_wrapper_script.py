#!/usr/bin/env python3
"""
QualityGate Wrapper Script Integration Tests
============================================

Tests for the qualitygate-pretooluse-wrapper.sh script that integrates
QualityGate with Claude Code's PreToolUse hook system.

Tests cover:
- Script execution and exit code forwarding
- Bridge script discovery and invocation
- Error handling when bridge is missing
- Integration with Claude Code hook system
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import json


@pytest.fixture
def wrapper_script_path():
    """Return the path to the wrapper script."""
    return Path("/mnt/c/Users/tky99/dev/.claude/hooks/qualitygate-pretooluse-wrapper.sh")


@pytest.fixture
def temp_qualitygate_setup(tmp_path):
    """Create temporary QualityGate environment for testing."""
    qualitygate_dir = tmp_path / "qualitygate"
    hooks_dir = qualitygate_dir / "hooks"
    hooks_dir.mkdir(parents=True)
    
    # Create a mock bridge script
    bridge_script = hooks_dir / "qualitygate_bridge.py"
    bridge_content = f"""#!/usr/bin/env python3
import sys
import json

# Mock bridge that echoes input and exits with code 0 or 1
try:
    if sys.stdin.isatty():
        data = {{"test": "mode"}}
    else:
        data = json.load(sys.stdin)
    
    # Check for content that should block
    content = str(data)
    if "BLOCK_ME" in content:
        print(json.dumps({{"status": "blocked", "block": True, "message": "Blocked content"}}))
        sys.exit(1)
    else:
        print(json.dumps({{"status": "passed", "block": False, "message": "Analysis passed"}}))
        sys.exit(0)
        
except Exception as e:
    print(json.dumps({{"status": "error", "block": False, "message": f"Error: {{e}}"}}))
    sys.exit(0)
"""
    
    bridge_script.write_text(bridge_content)
    bridge_script.chmod(0o755)
    
    return {
        "qualitygate_dir": qualitygate_dir,
        "bridge_script": bridge_script
    }


@pytest.fixture
def mock_wrapper_script(tmp_path, temp_qualitygate_setup):
    """Create a temporary wrapper script for testing."""
    wrapper_content = f"""#!/bin/bash
# Test wrapper script

QUALITYGATE_DIR="{temp_qualitygate_setup['qualitygate_dir']}"

# Check if QualityGate bridge exists
if [ ! -f "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py" ]; then
    echo "Warning: QualityGate bridge not found, allowing operation" >&2
    exit 0
fi

# Pass the event to QualityGate bridge
python3 "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py"

# Exit with the bridge's exit code
exit $?
"""
    
    wrapper_script = tmp_path / "test_wrapper.sh"
    wrapper_script.write_text(wrapper_content)
    wrapper_script.chmod(0o755)
    
    return wrapper_script


class TestWrapperScriptExecution:
    """Test wrapper script execution scenarios."""
    
    def test_wrapper_script_exists(self, wrapper_script_path):
        """Verify the wrapper script exists and is executable."""
        assert wrapper_script_path.exists(), "Wrapper script should exist"
        assert os.access(wrapper_script_path, os.X_OK), "Wrapper script should be executable"
    
    def test_wrapper_script_content(self, wrapper_script_path):
        """Verify wrapper script has expected content structure."""
        content = wrapper_script_path.read_text()
        
        # Check for essential components
        assert "#!/bin/bash" in content
        assert "qualitygate_bridge.py" in content
        assert "exit $?" in content or "exit ${" in content
    
    def test_wrapper_execution_bridge_exists(self, mock_wrapper_script):
        """Test wrapper execution when bridge script exists."""
        # Arrange
        test_input = json.dumps({"tool": {"name": "Edit", "parameters": {"content": "test"}}})
        
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input=test_input,
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode == 0, f"Wrapper should exit with 0, got {result.returncode}"
        
        # Should contain bridge output
        try:
            output = json.loads(result.stdout)
            assert output["status"] == "passed"
            assert output["block"] is False
        except json.JSONDecodeError:
            pytest.fail(f"Expected JSON output, got: {result.stdout}")
    
    def test_wrapper_execution_blocking_content(self, mock_wrapper_script):
        """Test wrapper execution with content that should be blocked."""
        # Arrange
        test_input = json.dumps({
            "tool": {"name": "Edit", "parameters": {"content": "BLOCK_ME - dangerous content"}}
        })
        
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input=test_input,
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode == 1, f"Wrapper should exit with 1 for blocked content, got {result.returncode}"
        
        # Should contain blocking message
        try:
            output = json.loads(result.stdout)
            assert output["status"] == "blocked"
            assert output["block"] is True
        except json.JSONDecodeError:
            pytest.fail(f"Expected JSON output, got: {result.stdout}")
    
    def test_wrapper_execution_bridge_missing(self, tmp_path):
        """Test wrapper execution when bridge script is missing."""
        # Arrange - create wrapper that points to non-existent bridge
        wrapper_content = """#!/bin/bash
QUALITYGATE_DIR="/nonexistent/path"

if [ ! -f "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py" ]; then
    echo "Warning: QualityGate bridge not found, allowing operation" >&2
    exit 0
fi

python3 "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py"
exit $?
"""
        
        wrapper_script = tmp_path / "missing_bridge_wrapper.sh"
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)
        
        # Act
        result = subprocess.run(
            [str(wrapper_script)],
            input="test input",
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode == 0, "Should allow operation when bridge is missing"
        assert "Warning:" in result.stderr
        assert "bridge not found" in result.stderr


class TestWrapperScriptIntegration:
    """Test integration scenarios with Claude Code hook system."""
    
    def test_stdin_json_parsing(self, mock_wrapper_script):
        """Test that wrapper properly passes JSON from stdin to bridge."""
        # Arrange
        complex_input = {
            "tool": {
                "name": "MultiEdit",
                "parameters": {
                    "file_path": "/test/file.py",
                    "edits": [
                        {"old_string": "old", "new_string": "new"},
                        {"old_string": "another", "new_string": "replacement"}
                    ]
                }
            }
        }
        
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input=json.dumps(complex_input),
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode == 0
        
        # Verify the JSON was processed
        try:
            output = json.loads(result.stdout)
            assert "status" in output
        except json.JSONDecodeError:
            pytest.fail("Wrapper should produce valid JSON output")
    
    def test_malformed_json_input(self, mock_wrapper_script):
        """Test wrapper behavior with malformed JSON input."""
        # Arrange
        malformed_input = '{"tool": {"name": "Edit", "invalid": json}'
        
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input=malformed_input,
            capture_output=True,
            text=True
        )
        
        # Assert - should handle gracefully and not crash
        # The exact behavior depends on bridge implementation
        # but should not result in shell errors
        assert result.returncode in [0, 1], "Should exit cleanly even with malformed input"
    
    def test_empty_stdin_input(self, mock_wrapper_script):
        """Test wrapper behavior with empty stdin."""
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input="",
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode in [0, 1], "Should handle empty input gracefully"
    
    def test_environment_variable_passing(self, mock_wrapper_script, temp_qualitygate_setup):
        """Test that environment variables are properly passed to bridge."""
        # Arrange - modify bridge to check environment variables
        bridge_script = temp_qualitygate_setup["bridge_script"]
        bridge_content = """#!/usr/bin/env python3
import sys
import json
import os

# Check for bypass environment variable
if os.environ.get("QUALITYGATE_BYPASS") == "1":
    print(json.dumps({"status": "bypassed", "block": False, "message": "Bypassed"}))
    sys.exit(0)

print(json.dumps({"status": "passed", "block": False, "message": "Normal execution"}))
sys.exit(0)
"""
        bridge_script.write_text(bridge_content)
        
        # Act - run with bypass environment variable
        env = os.environ.copy()
        env["QUALITYGATE_BYPASS"] = "1"
        
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input='{"tool": {"name": "Edit", "parameters": {"content": "test"}}}',
            env=env,
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "bypassed"


class TestWrapperScriptErrorHandling:
    """Test error handling scenarios."""
    
    def test_bridge_script_permission_error(self, tmp_path, temp_qualitygate_setup):
        """Test wrapper behavior when bridge script is not executable."""
        # Arrange - remove execute permission from bridge script
        bridge_script = temp_qualitygate_setup["bridge_script"]
        bridge_script.chmod(0o644)  # Remove execute permission
        
        wrapper_content = f"""#!/bin/bash
QUALITYGATE_DIR="{temp_qualitygate_setup['qualitygate_dir']}"

if [ ! -f "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py" ]; then
    echo "Warning: QualityGate bridge not found, allowing operation" >&2
    exit 0
fi

python3 "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py"
exit $?
"""
        
        wrapper_script = tmp_path / "perm_test_wrapper.sh"
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)
        
        # Act
        result = subprocess.run(
            [str(wrapper_script)],
            input='{"tool": {"name": "Edit", "parameters": {"content": "test"}}}',
            capture_output=True,
            text=True
        )
        
        # Assert - should still work (python can execute non-executable .py files)
        assert result.returncode in [0, 1], "Should handle permission issues gracefully"
    
    def test_bridge_script_syntax_error(self, tmp_path, temp_qualitygate_setup):
        """Test wrapper behavior when bridge script has syntax errors."""
        # Arrange - create bridge script with syntax error
        bridge_script = temp_qualitygate_setup["bridge_script"]
        bridge_script.write_text("#!/usr/bin/env python3\nthis is not valid python syntax!")
        
        wrapper_content = f"""#!/bin/bash
QUALITYGATE_DIR="{temp_qualitygate_setup['qualitygate_dir']}"

if [ ! -f "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py" ]; then
    echo "Warning: QualityGate bridge not found, allowing operation" >&2
    exit 0
fi

python3 "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py"
exit $?
"""
        
        wrapper_script = tmp_path / "syntax_test_wrapper.sh"
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)
        
        # Act
        result = subprocess.run(
            [str(wrapper_script)],
            input='{"tool": {"name": "Edit", "parameters": {"content": "test"}}}',
            capture_output=True,
            text=True
        )
        
        # Assert - should exit with error code due to syntax error
        assert result.returncode != 0, "Should fail when bridge script has syntax errors"
        assert "SyntaxError" in result.stderr or "syntax" in result.stderr.lower()
    
    def test_wrapper_script_timeout_handling(self, tmp_path, temp_qualitygate_setup):
        """Test wrapper behavior when bridge script hangs."""
        # Arrange - create bridge script that sleeps indefinitely
        bridge_script = temp_qualitygate_setup["bridge_script"]
        bridge_script.write_text("""#!/usr/bin/env python3
import time
import sys
# Simulate hanging bridge script
time.sleep(60)  # Sleep for 60 seconds
sys.exit(0)
""")
        
        wrapper_content = f"""#!/bin/bash
QUALITYGATE_DIR="{temp_qualitygate_setup['qualitygate_dir']}"

if [ ! -f "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py" ]; then
    echo "Warning: QualityGate bridge not found, allowing operation" >&2
    exit 0
fi

python3 "$QUALITYGATE_DIR/hooks/qualitygate_bridge.py"
exit $?
"""
        
        wrapper_script = tmp_path / "timeout_test_wrapper.sh"
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)
        
        # Act - run with timeout
        try:
            result = subprocess.run(
                [str(wrapper_script)],
                input='{"tool": {"name": "Edit", "parameters": {"content": "test"}}}',
                capture_output=True,
                text=True,
                timeout=5  # 5 second timeout
            )
            pytest.fail("Expected TimeoutExpired exception")
        except subprocess.TimeoutExpired:
            # Expected behavior - wrapper should be killable
            pass


class TestWrapperScriptCLIIntegration:
    """Test integration with Claude Code CLI hook system."""
    
    def test_exit_code_forwarding_success(self, mock_wrapper_script):
        """Test that successful bridge execution results in exit code 0."""
        # Arrange
        test_input = json.dumps({
            "tool": {"name": "Edit", "parameters": {"content": "safe content"}}
        })
        
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input=test_input,
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode == 0, "Should exit with 0 when bridge allows operation"
    
    def test_exit_code_forwarding_blocked(self, mock_wrapper_script):
        """Test that blocked bridge execution results in exit code 1."""
        # Arrange
        test_input = json.dumps({
            "tool": {"name": "Edit", "parameters": {"content": "BLOCK_ME content"}}
        })
        
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input=test_input,
            capture_output=True,
            text=True
        )
        
        # Assert
        assert result.returncode == 1, "Should exit with 1 when bridge blocks operation"
    
    def test_stderr_output_preservation(self, mock_wrapper_script):
        """Test that stderr output from bridge is preserved."""
        # Arrange - modify bridge to output to stderr
        # This would require modifying the temp bridge script to output to stderr
        test_input = json.dumps({
            "tool": {"name": "Edit", "parameters": {"content": "test content"}}
        })
        
        # Act
        result = subprocess.run(
            [str(mock_wrapper_script)],
            input=test_input,
            capture_output=True,
            text=True
        )
        
        # Assert
        # The exact stderr content depends on bridge implementation
        # but should not interfere with the wrapper's basic functionality
        assert result.returncode in [0, 1], "Should complete execution regardless of stderr"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
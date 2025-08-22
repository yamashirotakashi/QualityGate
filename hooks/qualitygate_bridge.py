#!/usr/bin/env python3
"""
QualityGate Hook Integration Bridge
==================================

Hook integration bridge that connects QualityGate's hook implementation 
with Claude Code's PreToolUse system.

This bridge script enables the 80+ quality patterns to work correctly
with Claude Code's actual hook system (PreToolUse/PreCompact) instead of
the expected before_edit/before_bash hooks.

Architecture:
- Input: Claude Code PreToolUse event data (JSON via stdin)
- Process: Extract tool information and route to appropriate QualityGate hook
- Output: QualityGate analysis results with blocking capability

Usage:
    Called automatically by Claude Code PreToolUse hooks.
    Not intended for direct execution.

Author: QualityGate AI Learning System
Version: 1.0.0
"""

import sys
import json
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - QualityGate Bridge - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/qualitygate_bridge.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

class QualityGateBridge:
    """Bridge between Claude Code PreToolUse hooks and QualityGate hooks."""
    
    def __init__(self):
        self.qualitygate_root = Path("/mnt/c/Users/tky99/dev/qualitygate")
        self.hooks_dir = self.qualitygate_root / "hooks"
        self.patterns_file = self.qualitygate_root / "config" / "patterns.json"
        
        # Tool mapping: Claude Code tools -> QualityGate hook scripts
        self.tool_mapping = {
            "Edit": "before_edit_qualitygate.py",
            "Write": "before_edit_qualitygate.py", 
            "MultiEdit": "before_edit_qualitygate.py",
            "NotebookEdit": "before_edit_qualitygate.py",
            "Bash": "before_bash_qualitygate.py",
            "BashOutput": "before_bash_qualitygate.py"
        }
        
        # Emergency bypass check
        self.bypass_enabled = self._check_bypass()
        
    def _check_bypass(self) -> bool:
        """Check if QualityGate bypass is enabled via environment variables."""
        return any([
            os.environ.get("BYPASS_DESIGN_HOOK") == "1",
            os.environ.get("QUALITYGATE_DISABLED") == "1",
            os.environ.get("QUALITYGATE_BYPASS") == "1"
        ])
    
    def _extract_tool_info(self, event_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Extract tool name and parameters from Claude Code event data."""
        try:
            tool_name = event_data.get("tool", {}).get("name", "unknown")
            tool_params = event_data.get("tool", {}).get("parameters", {})
            
            logger.info(f"Extracted tool: {tool_name} with params: {list(tool_params.keys())}")
            return tool_name, tool_params
            
        except Exception as e:
            logger.error(f"Failed to extract tool info: {e}")
            return "unknown", {}
    
    def _get_hook_script_path(self, tool_name: str) -> Optional[Path]:
        """Get the appropriate QualityGate hook script for the given tool."""
        hook_script = self.tool_mapping.get(tool_name)
        if not hook_script:
            logger.warning(f"No hook script mapped for tool: {tool_name}")
            return None
            
        script_path = self.hooks_dir / hook_script
        if not script_path.exists():
            logger.error(f"Hook script not found: {script_path}")
            return None
            
        return script_path
    
    def _prepare_hook_input(self, tool_name: str, tool_params: Dict[str, Any]) -> str:
        """Prepare input data for QualityGate hook scripts."""
        if tool_name in ["Edit", "Write", "MultiEdit", "NotebookEdit"]:
            # For editing tools, extract the content to be written
            content = ""
            if "content" in tool_params:
                content = tool_params["content"]
            elif "new_string" in tool_params:
                content = tool_params["new_string"]
            elif "edits" in tool_params:
                # MultiEdit case
                edits = tool_params["edits"]
                if isinstance(edits, list) and edits:
                    content = "\n".join([edit.get("new_string", "") for edit in edits])
            
            return content
            
        elif tool_name in ["Bash", "BashOutput"]:
            # For bash tools, extract the command
            return tool_params.get("command", "")
            
        else:
            # Fallback: convert params to string
            return json.dumps(tool_params, indent=2)
    
    def _execute_qualitygate_hook(self, script_path: Path, hook_input: str, tool_name: str) -> Tuple[bool, str]:
        """Execute QualityGate hook script and return (should_block, message)."""
        try:
            # Prepare environment: inject expected hook variables
            env = os.environ.copy()
            # Ensure QualityGate root is visible to downstream scripts
            env.setdefault("QUALITYGATE_ROOT", str(self.qualitygate_root))
            if tool_name in ["Edit", "Write", "MultiEdit", "NotebookEdit"]:
                env["CLAUDE_HOOK_MESSAGE"] = hook_input
            elif tool_name in ["Bash", "BashOutput"]:
                env["CLAUDE_HOOK_COMMAND"] = hook_input

            # Execute the QualityGate hook script
            process = subprocess.Popen(
                ["python", str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.qualitygate_root),
                env=env
            )
            
            stdout, stderr = process.communicate(input=hook_input, timeout=30)
            
            if process.returncode == 0:
                logger.info(f"QualityGate hook passed: {script_path.name}")
                return False, "QualityGate: Analysis passed"
            elif process.returncode in (1, 2):
                # Quality issue detected, should block (2 is CRITICAL per analyzer)
                logger.warning(f"QualityGate hook blocked: {script_path.name}")
                error_message = stderr.strip() or stdout.strip() or "Quality issue detected"
                return True, f"🚨 QualityGate Block: {error_message}"
            else:
                # Unexpected error, log but don't block
                logger.error(f"QualityGate hook error (rc={process.returncode}): {stderr}")
                return False, f"QualityGate: Hook error (continuing)"
                
        except subprocess.TimeoutExpired:
            logger.error(f"QualityGate hook timeout: {script_path.name}")
            process.kill()
            return False, "QualityGate: Hook timeout (continuing)"
        except Exception as e:
            logger.error(f"Failed to execute QualityGate hook: {e}")
            return False, f"QualityGate: Hook execution error (continuing)"
    
    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Claude Code PreToolUse event through QualityGate hooks."""
        logger.info(f"Processing QualityGate bridge event")
        
        # Check bypass first
        if self.bypass_enabled:
            logger.info("QualityGate bypass enabled, skipping analysis")
            return {
                "status": "bypassed",
                "message": "QualityGate bypassed via environment variable",
                "block": False
            }
        
        # Extract tool information
        tool_name, tool_params = self._extract_tool_info(event_data)
        
        # Get appropriate hook script
        hook_script = self._get_hook_script_path(tool_name)
        if not hook_script:
            logger.info(f"No QualityGate hook for tool: {tool_name}")
            return {
                "status": "no_hook",
                "message": f"No QualityGate hook configured for {tool_name}",
                "block": False
            }
        
        # Prepare input for hook script
        hook_input = self._prepare_hook_input(tool_name, tool_params)
        if not hook_input.strip():
            logger.info("No content to analyze, skipping QualityGate check")
            return {
                "status": "no_content", 
                "message": "No content to analyze",
                "block": False
            }
        
        # Execute QualityGate hook
        should_block, message = self._execute_qualitygate_hook(hook_script, hook_input, tool_name)
        
        result = {
            "status": "blocked" if should_block else "passed",
            "message": message,
            "block": should_block,
            "tool": tool_name,
            "hook_script": hook_script.name
        }
        
        logger.info(f"QualityGate result: {result['status']} - {message}")
        return result

def main():
    """Main entry point for QualityGate bridge."""
    try:
        # Read event data from stdin
        if not sys.stdin.isatty():
            event_data = json.load(sys.stdin)
        else:
            # Test mode: use sample data
            event_data = {
                "tool": {
                    "name": "Edit",
                    "parameters": {
                        "content": "とりあえず修正します",
                        "file_path": "/tmp/test.py"
                    }
                }
            }
        
        # Process through QualityGate bridge
        bridge = QualityGateBridge()
        result = bridge.process_event(event_data)
        
        # Output result
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result["block"]:
            sys.exit(1)  # Block the operation
        else:
            sys.exit(0)  # Allow the operation
            
    except Exception as e:
        logger.error(f"QualityGate bridge failed: {e}")
        print(json.dumps({
            "status": "error",
            "message": f"QualityGate bridge error: {str(e)}",
            "block": False  # Don't block on bridge errors
        }, indent=2))
        sys.exit(0)

# Claude Code PreToolUse Integration Script
def create_claude_code_wrapper():
    """Create wrapper script for Claude Code PreToolUse hook integration"""
    wrapper_script = '''#!/bin/bash
# qualitygate-pretooluse-wrapper.sh
# QualityGate PreToolUse Hook Wrapper for Claude Code
# Location: /mnt/c/Users/tky99/dev/.claude/hooks/qualitygate-pretooluse-wrapper.sh

# Set up environment
export PYTHONPATH="/mnt/c/Users/tky99/dev/qualitygate:$PYTHONPATH"
cd /mnt/c/Users/tky99/dev/qualitygate

# Parse Claude Code event data and execute QualityGate bridge
python3 hooks/qualitygate_bridge.py

# Capture exit code and forward appropriately
exit_code=$?

# Exit codes:
# 0 = Allow operation (QualityGate passed)
# 1 = Block operation (QualityGate failed/blocked)
exit $exit_code
'''
    
    wrapper_path = "/mnt/c/Users/tky99/dev/.claude/hooks/qualitygate-pretooluse-wrapper.sh"
    print(f"Wrapper script should be created at: {wrapper_path}")
    print("Content:")
    print(wrapper_script)
    return wrapper_script

def generate_claude_settings_config():
    """Generate Claude Code settings.json configuration for QualityGate integration"""
    
    qualitygate_config = {
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
    
    print("Claude Code settings.json configuration:")
    print(json.dumps(qualitygate_config, indent=2))
    return qualitygate_config

if __name__ == "__main__":
    print("=== QualityGate Claude Code Integration Setup ===")
    print()
    
    print("1. Creating Claude Code wrapper script...")
    create_claude_code_wrapper()
    print()
    
    print("2. Generating settings.json configuration...")
    generate_claude_settings_config()
    print()
    
    print("=== Integration Instructions ===")
    print("1. Create wrapper script at: /mnt/c/Users/tky99/dev/.claude/hooks/qualitygate-pretooluse-wrapper.sh")
    print("2. Make executable: chmod +x /mnt/c/Users/tky99/dev/.claude/hooks/qualitygate-pretooluse-wrapper.sh")
    print("3. Update Claude Code settings.json at: /home/tky99/.config/claude/settings.json")
    print("4. Add the QualityGate PreToolUse hook configuration to existing hooks section")
    print("5. Restart Claude Code to apply changes")

if __name__ == "__main__":
    main()

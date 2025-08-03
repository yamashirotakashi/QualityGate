#!/usr/bin/env python3
"""
QualityGate Hook Integration - Before Bash
Phase 1: Severity-based blocking for bash operations
"""

import sys
import os
import time
from pathlib import Path

# Add scripts directory to path for severity analyzer
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    from severity_analyzer import SeverityAnalyzer, check_bypass_conditions
except ImportError:
    # Fallback if severity_analyzer not available
    print("⚠️ QualityGate: severity_analyzer not found, skipping quality checks", file=sys.stderr)
    sys.exit(0)

def main():
    """Main hook entry point for before_bash"""
    start_time = time.time()
    
    # Check for bypass conditions
    if check_bypass_conditions():
        return 0
    
    # Get bash command from Claude Code hook environment
    bash_command = os.environ.get("CLAUDE_HOOK_COMMAND", "")
    bash_args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    if not bash_command and not bash_args:
        # No command to analyze
        return 0
    
    # Combine command for analysis
    full_command = f"{bash_command} {bash_args}"
    
    try:
        # Initialize analyzer
        analyzer = SeverityAnalyzer()
        
        # Analyze command
        finding = analyzer.analyze(full_command)
        
        if finding:
            severity = finding['severity']
            message = finding['message']
            action = analyzer.get_action_for_severity(severity)
            
            # Display finding with QualityGate prefix
            print(f"🔒 QualityGate {action['emoji']} {action['prefix']}: {message}", file=sys.stderr)
            print(f"🔍 コマンド: {full_command[:100]}{'...' if len(full_command) > 100 else ''}", file=sys.stderr)
            
            # Apply delay if configured (for warnings)
            if action['delay'] > 0:
                print(f"⏱️  QualityGate: {action['delay']}秒間停止しています...", file=sys.stderr)
                time.sleep(action['delay'])
            
            # Respect 5-second timeout constraint
            elapsed = time.time() - start_time
            if elapsed > 4.5:  # Leave 0.5s buffer
                print("⏰ QualityGate: タイムアウト接近、操作を許可します", file=sys.stderr)
                return 0
            
            # Return appropriate exit code
            if action['block']:
                print("🚫 QualityGate: 重大なセキュリティ違反によりBash操作をブロックしました", file=sys.stderr)
                print("💡 QualityGate: 緊急時は BYPASS_DESIGN_HOOK=1 でバイパス可能です", file=sys.stderr)
                return action['exit_code']
        
        return 0
        
    except Exception as e:
        # Fail safe - don't block on errors
        print(f"⚠️ QualityGate Error: {e}", file=sys.stderr)
        return 0

if __name__ == "__main__":
    sys.exit(main())
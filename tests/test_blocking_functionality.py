#!/usr/bin/env python3
"""
QualityGate Phase 1 - Blocking Functionality Tests
Tests the severity-based blocking system
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from severity_analyzer import SeverityAnalyzer

def test_critical_patterns():
    """Test critical patterns that should block execution"""
    print("🧪 Testing CRITICAL patterns (should block with exit code 2)...")
    
    test_cases = [
        ("API Key", "sk_test_1234567890abcdef1234567890abcdef"),
        ("AWS Key", "AKIA1234567890123456"),
        ("Google API", "AIza1234567890abcdefghijklmnopqrstuvwxyz123"),
        ("Slack Token", "xoxb-1234567890-1234567890123-abcdefghijklmnopqrstuvwx"),
        ("GitHub Token", "ghp_1234567890abcdef1234567890abcdef123456"),
        ("Dangerous RM", "rm -rf /"),
        ("Sudo RM", "sudo rm -rf /home/user"),
        ("Direct Eval", "eval(user_input)"),
        ("Shell Injection", "subprocess.call(cmd, shell=True)")
    ]
    
    analyzer = SeverityAnalyzer()
    
    for test_name, test_input in test_cases:
        finding = analyzer.analyze(test_input)
        if finding and finding['severity'] == 'CRITICAL':
            action = analyzer.get_action_for_severity('CRITICAL')
            print(f"✅ {test_name}: BLOCKED (exit code {action['exit_code']})")
        else:
            print(f"❌ {test_name}: NOT BLOCKED (should be CRITICAL)")
    
    print()

def test_high_patterns():
    """Test high severity patterns that should warn but not block"""
    print("🧪 Testing HIGH patterns (should warn but not block)...")
    
    test_cases = [
        ("Band-aid Fix JP", "とりあえず修正"),
        ("Band-aid Fix EN", "temporary fix"),
        ("Incomplete TODO", "TODO fix this later"),
        ("Hardcoded URL", "http://example.com/api"),
        ("Silent Exception", "except: pass"),
        ("Hardcoded IP", "127.0.0.1:8080")
    ]
    
    analyzer = SeverityAnalyzer()
    
    for test_name, test_input in test_cases:
        finding = analyzer.analyze(test_input)
        if finding and finding['severity'] == 'HIGH':
            action = analyzer.get_action_for_severity('HIGH')
            print(f"⚠️  {test_name}: WARNING (exit code {action['exit_code']})")
        else:
            print(f"ℹ️  {test_name}: No warning (might be expected)")
    
    print()

def test_bypass_functionality():
    """Test bypass functionality"""
    print("🧪 Testing bypass functionality...")
    
    # Test with bypass enabled
    os.environ['BYPASS_DESIGN_HOOK'] = '1'
    
    # Create temporary script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import sys
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')
from severity_analyzer import main
sys.exit(main())
""")
        temp_script = f.name
    
    try:
        # Test critical pattern with bypass
        result = subprocess.run([
            sys.executable, temp_script, "sk_test_1234567890abcdef1234567890abcdef"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Bypass: WORKING (critical pattern allowed)")
        else:
            print(f"❌ Bypass: NOT WORKING (exit code {result.returncode})")
            
        # Check for bypass message
        if "bypassed" in result.stdout.lower():
            print("✅ Bypass: Message displayed correctly")
        
    finally:
        # Clean up
        os.unlink(temp_script)
        del os.environ['BYPASS_DESIGN_HOOK']
    
    print()

def test_hook_integration():
    """Test hook integration with environment variables"""
    print("🧪 Testing hook integration...")
    
    # Set up hook environment variables
    os.environ['CLAUDE_HOOK_COMMAND'] = 'git commit -m "とりあえず修正"'
    os.environ['CLAUDE_HOOK_MESSAGE'] = 'temporary fix for the issue'
    
    # Test edit hook
    edit_hook = Path(__file__).parent.parent / "hooks" / "before_edit_qualitygate.py"
    if edit_hook.exists():
        result = subprocess.run([sys.executable, str(edit_hook)], 
                              capture_output=True, text=True)
        print(f"📝 Edit Hook: exit code {result.returncode}")
        if result.stderr:
            print(f"   Output: {result.stderr.strip()}")
    
    # Test bash hook
    bash_hook = Path(__file__).parent.parent / "hooks" / "before_bash_qualitygate.py"
    if bash_hook.exists():
        result = subprocess.run([sys.executable, str(bash_hook)], 
                              capture_output=True, text=True)
        print(f"⚡ Bash Hook: exit code {result.returncode}")
        if result.stderr:
            print(f"   Output: {result.stderr.strip()}")
    
    # Clean up environment
    del os.environ['CLAUDE_HOOK_COMMAND']
    del os.environ['CLAUDE_HOOK_MESSAGE']
    
    print()

def test_performance():
    """Test performance within 5-second constraint"""
    print("🧪 Testing performance (5-second timeout constraint)...")
    
    import time
    
    analyzer = SeverityAnalyzer()
    
    # Test with large content
    large_content = "print('test')\n" * 1000 + "sk_test_1234567890abcdef1234567890abcdef"
    
    start_time = time.time()
    finding = analyzer.analyze(large_content)
    elapsed = time.time() - start_time
    
    print(f"⏱️  Analysis time: {elapsed:.3f} seconds")
    
    if elapsed < 4.5:  # Leave buffer for hook processing
        print("✅ Performance: WITHIN LIMITS")
    else:
        print("❌ Performance: TOO SLOW")
    
    if finding and finding['severity'] == 'CRITICAL':
        print("✅ Large Content: CRITICAL pattern detected correctly")
    else:
        print("❌ Large Content: Failed to detect CRITICAL pattern")
    
    print()

def main():
    """Run all tests"""
    print("🔒 QualityGate Phase 1 - Blocking Functionality Tests")
    print("=" * 60)
    
    test_critical_patterns()
    test_high_patterns()
    test_bypass_functionality()
    test_hook_integration()
    test_performance()
    
    print("🏁 Test Suite Complete")
    print("=" * 60)
    print("📋 Summary:")
    print("   - CRITICAL patterns should block with exit code 2")
    print("   - HIGH patterns should warn with exit code 0")
    print("   - Bypass functionality should allow emergency override")
    print("   - Hook integration should work with Claude Code")
    print("   - Performance should complete within 4.5 seconds")

if __name__ == "__main__":
    main()
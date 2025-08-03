#!/usr/bin/env python3
"""
QualityGate Status Checker
Displays current implementation status and configuration
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and return status"""
    if Path(file_path).exists():
        return f"✅ {description}"
    else:
        return f"❌ {description} (Missing)"

def check_executable(file_path):
    """Check if a file is executable"""
    path = Path(file_path)
    if path.exists() and os.access(path, os.X_OK):
        return "✅ Executable"
    elif path.exists():
        return "⚠️  Exists but not executable"
    else:
        return "❌ Missing"

def check_phase_status():
    """Check current phase implementation status"""
    print("📊 QualityGate Implementation Status")
    print("=" * 50)
    
    # Phase 1 Core Components
    print("\n🔧 Phase 1 Core Components:")
    base_dir = Path("/mnt/c/Users/tky99/dev/qualitygate")
    
    components = [
        (base_dir / "scripts" / "severity_analyzer.py", "Severity Analyzer"),
        (base_dir / "config" / "patterns.json", "Pattern Configuration"),
        (base_dir / "hooks" / "before_edit_qualitygate.py", "Edit Hook"),
        (base_dir / "hooks" / "before_bash_qualitygate.py", "Bash Hook"),
        (base_dir / "tests" / "test_blocking_functionality.py", "Test Suite"),
    ]
    
    for file_path, description in components:
        print(f"  {check_file_exists(file_path, description)}")
    
    # Executable Status
    print("\n🏃 Executable Status:")
    executables = [
        (base_dir / "scripts" / "severity_analyzer.py", "Severity Analyzer"),
        (base_dir / "hooks" / "before_edit_qualitygate.py", "Edit Hook"),
        (base_dir / "hooks" / "before_bash_qualitygate.py", "Bash Hook"),
        (base_dir / "tests" / "test_blocking_functionality.py", "Test Suite"),
    ]
    
    for file_path, description in executables:
        print(f"  {description}: {check_executable(file_path)}")

def check_pattern_configuration():
    """Check pattern configuration status"""
    print("\n📋 Pattern Configuration:")
    
    config_file = Path("/mnt/c/Users/tky99/dev/qualitygate/config/patterns.json")
    
    if not config_file.exists():
        print("  ❌ patterns.json not found")
        return
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Count patterns by severity
        critical_count = 0
        high_count = 0
        info_count = 0
        
        for severity, categories in config.items():
            if severity == "CRITICAL" and isinstance(categories, dict):
                for category, content in categories.items():
                    if isinstance(content, dict) and "patterns" in content:
                        critical_count += len(content["patterns"])
            elif severity == "HIGH" and isinstance(categories, dict):
                for category, content in categories.items():
                    if isinstance(content, dict) and "patterns" in content:
                        high_count += len(content["patterns"])
            elif severity == "INFO" and isinstance(categories, dict):
                for category, content in categories.items():
                    if isinstance(content, dict) and "patterns" in content:
                        info_count += len(content["patterns"])
        
        print(f"  🔴 CRITICAL patterns: {critical_count}")
        print(f"  🟡 HIGH patterns: {high_count}")
        print(f"  🔵 INFO patterns: {info_count}")
        print(f"  📊 Total patterns: {critical_count + high_count + info_count}")
        
        # Check version info
        version = config.get("version", "Unknown")
        last_updated = config.get("last_updated", "Unknown")
        print(f"  📌 Version: {version}")
        print(f"  📅 Last updated: {last_updated}")
        
    except Exception as e:
        print(f"  ❌ Error reading configuration: {e}")

def check_claude_code_integration():
    """Check Claude Code hook integration status"""
    print("\n🔗 Claude Code Integration:")
    
    # Check for hooks configuration
    hooks_config_files = [
        "/mnt/c/Users/tky99/dev/.claude_hooks_config.json",
        "/mnt/c/Users/tky99/dev/.claude_hooks_config_optimized.json",
        "/mnt/c/Users/tky99/DEV/.claude_hooks_config.json"
    ]
    
    found_config = False
    for config_file in hooks_config_files:
        if Path(config_file).exists():
            print(f"  ✅ Found hooks config: {config_file}")
            found_config = True
            break
    
    if not found_config:
        print("  ❌ No Claude Code hooks configuration found")
        print("  💡 Need to integrate with existing hook system")
    
    # Check existing design protection hook
    design_hook = Path("/mnt/c/Users/tky99/dev/scripts/design_protection_hook.py")
    if design_hook.exists():
        print("  ✅ Existing design protection hook found")
        print("  🔄 Integration needed with QualityGate system")
    else:
        print("  ❌ Existing design protection hook not found")

def check_bypass_mechanisms():
    """Check bypass mechanism status"""
    print("\n🔓 Bypass Mechanisms:")
    
    bypass_vars = ['BYPASS_DESIGN_HOOK', 'QUALITYGATE_DISABLED', 'EMERGENCY_BYPASS']
    
    active_bypasses = []
    for var in bypass_vars:
        value = os.environ.get(var, '')
        if value.lower() in ['1', 'true', 'yes']:
            active_bypasses.append(var)
    
    if active_bypasses:
        print(f"  ⚠️  Active bypasses: {', '.join(active_bypasses)}")
    else:
        print("  ✅ No active bypasses (normal operation)")
    
    print("  💡 Available bypass variables:")
    for var in bypass_vars:
        print(f"     - {var}")

def show_next_steps():
    """Show next steps for Phase 1 completion"""
    print("\n🚀 Next Steps for Phase 1 Completion:")
    
    steps = [
        "1. Run test suite to verify functionality",
        "2. Integrate with Claude Code hook system",
        "3. Test blocking functionality in real environment",
        "4. Monitor performance and adjust patterns",
        "5. Collect feedback and prepare for Phase 2"
    ]
    
    for step in steps:
        print(f"  📋 {step}")

def main():
    """Main status check function"""
    check_phase_status()
    check_pattern_configuration()
    check_claude_code_integration()
    check_bypass_mechanisms()
    show_next_steps()
    
    print("\n" + "=" * 50)
    print("🔒 QualityGate Status Check Complete")

if __name__ == "__main__":
    main()
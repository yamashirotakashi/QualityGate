# QualityGate Essential Commands

## Development Commands
```bash
# Run severity analyzer directly
python scripts/severity_analyzer.py "test content here"

# Run optimized analyzer with performance testing
python scripts/optimized_severity_analyzer.py

# Check project status
python scripts/qualitygate_status.py

# Run performance optimizer tests
python scripts/performance_optimizer.py
```

## Testing Commands
```bash
# Run test suite (when implemented)
python tests/test_blocking_functionality.py

# Test hook integration
./hooks/before_edit_qualitygate.py "test content"
./hooks/before_bash_qualitygate.py "test command"
```

## Configuration Management
```bash
# View current patterns
cat config/patterns.json

# Check hook configuration
ls -la /mnt/c/Users/tky99/dev/.claude_hooks_config*.json
```

## Bypass Mechanisms
```bash
# Emergency bypass
export EMERGENCY_BYPASS=1

# Disable quality gate temporarily
export QUALITYGATE_DISABLED=1

# Legacy bypass
export BYPASS_DESIGN_HOOK=1
```

## Special Project Prompts
```bash
[QGate]           # Switch to QualityGate project
[QG]              # Short form
[QGate] status    # Show implementation status
[QGate] test      # Run quality gate tests
[QGate] config    # View/modify configuration
[QGate] bypass    # Emergency bypass function
[QGate] stats     # Show statistics and effectiveness
```
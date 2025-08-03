# QualityGate Task Completion Workflow

## When Task is Completed

### 1. Code Quality Checks
```bash
# Run the analyzer on your own changes
python scripts/optimized_severity_analyzer.py

# Check for any critical patterns in your code
python scripts/severity_analyzer.py "$(git diff)"
```

### 2. Performance Validation
```bash
# Ensure changes don't break 5-second constraint
python scripts/performance_optimizer.py
```

### 3. Integration Testing
```bash
# Test hook integration
./hooks/optimized_before_edit.py "test content"
./hooks/optimized_before_bash.py "test command"
```

### 4. Configuration Updates
- Update `config/patterns.json` if new patterns added
- Update version and last_updated fields
- Test pattern validation

### 5. Documentation Updates
- Update PHASE*_COMPLETION_REPORT.md if major milestone
- Update QUALITYGATE_PROJECT.md for architecture changes
- Update this memory file for new commands/workflows

### 6. Status Verification
```bash
# Final status check
python scripts/qualitygate_status.py

# Verify no bypass conditions are active
env | grep -E "(BYPASS|QUALITYGATE_DISABLED|EMERGENCY)"
```

## Pre-commit Checklist
- [ ] No hardcoded secrets in changes
- [ ] No band-aid fix patterns
- [ ] Performance constraint maintained (<5s)
- [ ] All tests pass
- [ ] Configuration files valid JSON
- [ ] Documentation updated
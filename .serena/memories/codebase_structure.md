# QualityGate Codebase Structure

## Directory Structure
```
/mnt/c/Users/tky99/dev/qualitygate/
├── .serena/                    # Serena project configuration
├── config/
│   ├── patterns.json          # Pattern definitions by severity
│   └── optimized_hooks_config.json  # Hook configuration
├── docs/                       # Project documentation
├── hooks/                      # Claude Code hook implementations
│   ├── before_edit_qualitygate.py   # Edit operation hooks
│   ├── before_bash_qualitygate.py   # Bash command hooks
│   ├── optimized_before_edit.py     # Phase 2 optimized edit hook
│   ├── optimized_before_bash.py     # Phase 2 optimized bash hook
│   └── unified_quality_hook.py      # Unified hook system
├── scripts/                    # Core analysis engines
│   ├── severity_analyzer.py          # Phase 1 analyzer
│   ├── optimized_severity_analyzer.py # Phase 2 optimized analyzer
│   ├── performance_optimizer.py      # Performance optimization engine
│   └── qualitygate_status.py        # Status checker
├── tests/                      # Test suite
└── README.md, CLAUDE.md, etc.  # Project documentation
```

## Key Components by Phase

### Phase 1 (Completed)
- `scripts/severity_analyzer.py` - Basic severity analysis
- `hooks/before_*_qualitygate.py` - Basic hook integration
- `config/patterns.json` - Pattern configuration

### Phase 2 (Current - Optimization Focus)
- `scripts/optimized_severity_analyzer.py` - High-performance analyzer
- `scripts/performance_optimizer.py` - Caching and optimization
- `hooks/optimized_before_*.py` - Optimized hook implementations

### Phase 3 (Planned - AI Learning)
- AST analysis engine (planned)
- Statistical learning components (planned)
- Predictive quality detection (planned)
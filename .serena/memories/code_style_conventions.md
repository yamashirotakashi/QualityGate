# QualityGate Code Style and Conventions

## Code Organization
- **Modular Structure**: Separate files for different concerns
  - `severity_analyzer.py` - Core analysis logic
  - `performance_optimizer.py` - Performance optimization
  - `optimized_severity_analyzer.py` - Phase 2 optimized version
- **Config-driven**: JSON-based pattern configuration in `config/patterns.json`

## Naming Conventions
- **Classes**: PascalCase (e.g., `SeverityAnalyzer`, `PerformanceOptimizer`)
- **Methods**: snake_case (e.g., `analyze_input_optimized`, `get_content_hash`)
- **Constants**: UPPER_CASE (e.g., `CRITICAL`, `HIGH`, `INFO`)
- **Private Methods**: Leading underscore (e.g., `_load_patterns_cached`)

## Docstring Style
- **Triple quotes** for all docstrings
- **Japanese descriptions** for user-facing messages
- **Clear parameter documentation** with types when complex

## Error Handling
- **Graceful Degradation**: Never block on analyzer errors
- **Fallback Patterns**: Default patterns when config fails
- **Silent Failures**: Continue execution even on regex errors

## Performance Patterns
- **Early Returns**: Check bypass conditions first
- **Timeout Constraints**: Respect 5-second limit with early exits
- **Cache-first**: Always check cache before computation
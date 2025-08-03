# QualityGate Technology Stack

## Core Technologies
- **Language**: Python 3.x
- **Pattern Matching**: Regular expressions (re module)
- **Caching**: In-memory dictionaries with MD5 hashing
- **Configuration**: JSON-based pattern configuration
- **Integration**: Claude Code Hook System

## Key Libraries
- `re` - Regular expression pattern matching
- `json` - Configuration file handling  
- `hashlib` - Content hashing for caching
- `pathlib` - Modern file path handling
- `time` - Performance monitoring
- `os` - Environment variable management

## Architecture Patterns
- **Singleton Pattern**: PerformanceOptimizer (global instance)
- **Strategy Pattern**: Severity-based analysis rules
- **Caching Pattern**: Multi-level caching (pattern cache, skip cache)
- **Factory Pattern**: Action configuration by severity

## Performance Optimizations
- **Content Hashing**: MD5-based cache keys
- **Multi-level Caching**: Pattern cache + skip cache for safe content
- **Early Exit**: Bypass conditions checked first
- **Size Optimization**: Large content truncation with keyword extraction
- **Compiled Patterns**: Pre-compiled regex caching
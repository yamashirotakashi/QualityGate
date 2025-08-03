#!/usr/bin/env python3
"""
HIGHパターンの個別テスト
"""

import sys
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')

from optimized_severity_analyzer import OptimizedSeverityAnalyzer

def test_high_patterns():
    analyzer = OptimizedSeverityAnalyzer()
    
    test_cases = [
        "とりあえずこれで修正",
        "暫定対応として実装", 
        "TODO: 後で修正",
        "FIXME later",
    ]
    
    # 設定を確認
    config = analyzer._load_patterns_cached()
    high_patterns = analyzer._extract_patterns_by_severity(config, "HIGH")
    print(f"HIGH パターン数: {len(high_patterns)}")
    
    for pattern, message in high_patterns.items():
        print(f"  {pattern} -> {message}")
    print()
    
    for test_input in test_cases:
        severity, message, action = analyzer.analyze_input_optimized(test_input)
        emoji = action.get('emoji', '❓')
        prefix = action.get('prefix', severity)
        print(f"入力: {test_input}")
        print(f"結果: {emoji} {prefix} - {message}")
        print()

if __name__ == "__main__":
    test_high_patterns()
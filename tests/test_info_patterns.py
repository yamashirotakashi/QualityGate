#!/usr/bin/env python3
"""
INFOパターンの個別テスト
"""

import sys
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')

from optimized_severity_analyzer import OptimizedSeverityAnalyzer

def test_info_patterns():
    analyzer = OptimizedSeverityAnalyzer()
    
    test_cases = [
        "console.log('debug info')",
        "print('debug message')",
        "debugger;",
        "pdb.set_trace()",
        "	タブ文字入り",  # タブ文字
        "行末スペース  ", # 行末スペース
        "var oldVariable = 'test';",  # JavaScript var
    ]
    
    # 設定を確認
    config = analyzer._load_patterns_cached()
    info_patterns = analyzer._extract_patterns_by_severity(config, "INFO")
    print(f"INFO パターン数: {len(info_patterns)}")
    
    for pattern, message in info_patterns.items():
        print(f"  {pattern} -> {message}")
    print()
    
    for test_input in test_cases:
        severity, message, action = analyzer.analyze_input_optimized(test_input)
        emoji = action.get('emoji', '❓')
        prefix = action.get('prefix', severity)
        print(f"入力: {repr(test_input)}")
        print(f"結果: {emoji} {prefix} - {message}")
        print()

if __name__ == "__main__":
    test_info_patterns()
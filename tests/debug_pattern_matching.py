#!/usr/bin/env python3
"""
QualityGate パターンマッチング デバッグ
パターン検出の問題を特定するためのデバッグスクリプト
"""

import sys
import json
import re
from pathlib import Path

# 最適化Analyzerをインポート
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')
from optimized_severity_analyzer import OptimizedSeverityAnalyzer

def debug_pattern_loading():
    """パターン読み込みのデバッグ"""
    print("🔍 パターン読み込みデバッグ")
    print("=" * 50)
    
    config_path = Path("/mnt/c/Users/tky99/dev/qualitygate/config/patterns.json")
    
    if not config_path.exists():
        print("❌ 設定ファイルが存在しません")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    analyzer = OptimizedSeverityAnalyzer()
    
    # CRITICAL パターンを抽出
    critical_patterns = analyzer._extract_patterns_by_severity(config, "CRITICAL")
    print(f"📊 CRITICAL パターン数: {len(critical_patterns)}")
    
    for pattern, message in critical_patterns.items():
        print(f"   {pattern} -> {message}")
    
    print()
    
    # HIGH パターンを抽出
    high_patterns = analyzer._extract_patterns_by_severity(config, "HIGH")
    print(f"📊 HIGH パターン数: {len(high_patterns)}")
    
    for pattern, message in high_patterns.items():
        print(f"   {pattern} -> {message}")
    
    print()
    
    # INFO パターンを抽出
    info_patterns = analyzer._extract_patterns_by_severity(config, "INFO")
    print(f"📊 INFO パターン数: {len(info_patterns)}")
    
    for pattern, message in info_patterns.items():
        print(f"   {pattern} -> {message}")

def debug_direct_pattern_matching():
    """直接パターンマッチングのデバッグ"""
    print("🧪 直接パターンマッチングデバッグ")
    print("=" * 50)
    
    test_cases = [
        ("sk_live_abc123def456ghi789jkl012mno345", r"(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}"),
        ("AKIA1234567890123456", r"AKIA[0-9A-Z]{16}"),
        ("rm -rf /", r"rm\\s+-rf\\s+/"),
        ("sudo rm -rf", r"sudo\\s+rm\\s+-rf"),
        ("とりあえずこれで修正", r"とりあえず|暫定対応|一時的"),
        ("TODO: 後で修正", r"TODO|FIXME"),
    ]
    
    for test_input, pattern in test_cases:
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            match = compiled_pattern.search(test_input)
            
            if match:
                print(f"✅ マッチ: '{test_input}' -> '{pattern}'")
                print(f"   マッチした部分: '{match.group()}'")
            else:
                print(f"❌ 非マッチ: '{test_input}' -> '{pattern}'")
                
        except re.error as e:
            print(f"💥 パターンエラー: '{pattern}' -> {e}")
        
        print()

def debug_analyzer_step_by_step():
    """Analyzerのステップバイステップデバッグ"""
    print("🔬 Analyzer ステップバイステップデバッグ")
    print("=" * 50)
    
    analyzer = OptimizedSeverityAnalyzer()
    test_input = "sk_live_abc123def456ghi789jkl012mno345"
    
    print(f"入力: {test_input}")
    
    # 設定読み込み
    config = analyzer._load_patterns_cached()
    print(f"設定読み込み: {'✅ 成功' if config else '❌ 失敗'}")
    
    # CRITICAL パターン抽出
    critical_patterns = analyzer._extract_patterns_by_severity(config, "CRITICAL")
    print(f"CRITICAL パターン: {len(critical_patterns)}個")
    
    # 最適化エンジンでのマッチング
    from scripts.performance_optimizer import get_optimizer
    optimizer = get_optimizer()
    
    pattern, message = optimizer.analyze_with_cache(test_input, critical_patterns, "CRITICAL")
    print(f"最適化マッチング結果: パターン='{pattern}', メッセージ='{message}'")
    
    # 実際の分析実行
    severity, message, action = analyzer.analyze_input_optimized(test_input)
    print(f"最終結果: severity='{severity}', message='{message}', action={action}")

def main():
    """デバッグメイン"""
    print("🐛 QualityGate パターンマッチング デバッグ")
    print("=" * 60)
    print()
    
    debug_pattern_loading()
    print()
    
    debug_direct_pattern_matching()
    print()
    
    debug_analyzer_step_by_step()

if __name__ == "__main__":
    main()
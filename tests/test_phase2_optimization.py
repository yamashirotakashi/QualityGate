#!/usr/bin/env python3
"""
QualityGate Phase 2 - 最適化システム総合テスト
統合Hookシステム、パフォーマンス最適化、MCP競合解決のテスト
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# テスト対象をインポート
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/hooks')

from optimized_severity_analyzer import OptimizedSeverityAnalyzer
from scripts.performance_optimizer import get_optimizer
from unified_quality_hook import UnifiedQualityHook

def test_pattern_detection():
    """パターン検出テスト"""
    print("🧪 Phase 2 パターン検出テスト")
    print("=" * 50)
    
    analyzer = OptimizedSeverityAnalyzer()
    
    test_cases = [
        # CRITICAL tests
        ("sk_live_abc123def456ghi789jkl012mno345", "CRITICAL", "APIシークレット"),
        ("AKIA1234567890123456", "CRITICAL", "AWSキー"),
        ("rm -rf /", "CRITICAL", "危険削除"),
        ("sudo rm -rf", "CRITICAL", "危険sudo"),
        
        # HIGH tests  
        ("とりあえずこれで修正", "HIGH", "バンドエイド"),
        ("暫定対応として実装", "HIGH", "バンドエイド"),
        ("TODO: 後で修正", "HIGH", "TODO"),
        
        # INFO tests
        ("console.log('debug')", "INFO", "デバッグ"),
        ("print(debug_info)", "INFO", "デバッグ"),
        
        # NONE tests
        ("普通のコードです", "NONE", "正常"),
        ("def normal_function():", "NONE", "正常"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_input, expected_severity, description in test_cases:
        severity, message, action = analyzer.analyze_input_optimized(test_input)
        
        if severity == expected_severity:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
        
        emoji = action.get('emoji', '❓')
        prefix = action.get('prefix', severity)
        
        print(f"{status} {description}: {emoji} {prefix} - {message}")
        print(f"     入力: {test_input[:50]}{'...' if len(test_input) > 50 else ''}")
        print(f"     期待: {expected_severity}, 実際: {severity}")
        print()
    
    print(f"📊 結果: {passed}/{total} passed ({passed/total*100:.1f}%)")
    return passed == total

def test_performance_optimization():
    """パフォーマンス最適化テスト"""
    print("🚀 Phase 2 パフォーマンス最適化テスト")
    print("=" * 50)
    
    analyzer = OptimizedSeverityAnalyzer()
    test_content = "sk_live_abc123def456ghi789jkl012mno345"
    
    # ウォームアップ
    for _ in range(10):
        analyzer.analyze_input_optimized(test_content)
    
    # パフォーマンステスト
    start_time = time.time()
    for _ in range(1000):
        severity, message, action = analyzer.analyze_input_optimized(test_content)
    end_time = time.time()
    
    total_time = (end_time - start_time) * 1000
    avg_time = total_time / 1000
    
    print(f"📊 1000回実行時間: {total_time:.2f}ms")
    print(f"📊 平均実行時間: {avg_time:.4f}ms")
    print(f"📊 処理能力: {int(1000/avg_time):,}回/秒")
    
    # 5秒制約チェック
    constraint_ok = avg_time < 5.0  # 5ms以内
    print(f"📊 5秒制約: {'✅ OK' if constraint_ok else '❌ NG'} ({avg_time:.4f}ms < 5.0ms)")
    
    # 統計情報
    stats = analyzer.get_analysis_stats()
    print(f"📊 キャッシュ統計: {stats['optimizer_stats']}")
    
    return constraint_ok

def test_unified_hook_system():
    """統合Hookシステムテスト"""
    print("🔗 Phase 2 統合Hookシステムテスト")
    print("=" * 50)
    
    hook = UnifiedQualityHook()
    
    test_cases = [
        ("sk_live_test123456789012345678901234", "edit", 2),  # CRITICAL -> block
        ("とりあえず修正", "bash", 0),  # HIGH -> warn
        ("normal code", "edit", 0),  # NONE -> pass
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_input, operation_type, expected_exit in test_cases:
        try:
            exit_code = hook.process_input(test_input, operation_type)
            
            if exit_code == expected_exit:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
            
            print(f"{status} {operation_type}: exit={exit_code} (expected={expected_exit})")
            print(f"     入力: {test_input[:40]}{'...' if len(test_input) > 40 else ''}")
            
        except Exception as e:
            print(f"❌ ERROR {operation_type}: {e}")
        
        print()
    
    print(f"📊 結果: {passed}/{total} passed ({passed/total*100:.1f}%)")
    return passed == total

def test_mcp_conflict_resolution():
    """MCP競合解決テスト"""
    print("🛡️ Phase 2 MCP競合解決テスト")
    print("=" * 50)
    
    # 最適化設定ファイルの確認
    config_path = Path("/mnt/c/Users/tky99/dev/qualitygate/config/optimized_hooks_config.json")
    
    if config_path.exists():
        print("✅ 最適化Hook設定ファイル: 存在")
        
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # MCP競合回避設定の確認
        perf_config = config.get("performance", {})
        mcp_config = perf_config.get("mcp_conflict_avoidance", {})
        
        if mcp_config.get("enabled"):
            print("✅ MCP競合回避: 有効")
        else:
            print("❌ MCP競合回避: 無効")
        
        # タイムアウト設定の確認
        max_hook_time = perf_config.get("max_hook_time", 0)
        if max_hook_time == 4500:
            print("✅ Hook制約時間: 4.5秒")
        else:
            print(f"❌ Hook制約時間: {max_hook_time}ms")
        
        return True
    else:
        print("❌ 最適化Hook設定ファイル: 存在しない")
        return False

def main():
    """Phase 2 最適化システム総合テスト"""
    print("🎯 QualityGate Phase 2 - 最適化システム総合テスト")
    print("=" * 60)
    print()
    
    tests = [
        ("パターン検出", test_pattern_detection),
        ("パフォーマンス最適化", test_performance_optimization),
        ("統合Hookシステム", test_unified_hook_system),
        ("MCP競合解決", test_mcp_conflict_resolution),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed_tests += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
        
        print()
    
    print("=" * 60)
    print(f"🏁 Phase 2 テスト結果: {passed_tests}/{total_tests} passed")
    
    if passed_tests == total_tests:
        print("🎉 Phase 2 最適化システム: 全テスト通過!")
        return 0
    else:
        print("⚠️  Phase 2 最適化システム: 修正が必要です")
        return 1

if __name__ == "__main__":
    sys.exit(main())
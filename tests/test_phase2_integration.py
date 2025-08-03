#!/usr/bin/env python3
"""
Phase 2 統合テストスイート
最適化システム全体の総合的な動作検証
"""

import sys
import time
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')

from optimized_severity_analyzer import OptimizedSeverityAnalyzer
from scripts.performance_optimizer import get_optimizer

def test_phase2_integration():
    """Phase 2統合テスト実行"""
    print("🚀 QualityGate Phase 2 統合テストスイート")
    print("=" * 60)
    
    analyzer = OptimizedSeverityAnalyzer()
    optimizer = get_optimizer()
    
    # テストケース定義
    test_cases = [
        # CRITICAL パターン
        ("sk_live_abc123def456ghi789jkl012mno345", "CRITICAL", "ハードコードされたAPIシークレットが検出されました"),
        ("AKIA1234567890123456", "CRITICAL", "ハードコードされたAWSアクセスキーIDが検出されました"),
        ("rm -rf /", "CRITICAL", "危険な再帰的削除コマンドが検出されました"),
        ("sudo rm -rf /important", "CRITICAL", "危険なsudo削除コマンドが検出されました"),
        
        # HIGH パターン
        ("とりあえずこれで修正", "HIGH", "バンドエイド修正の可能性が検出されました"),
        ("TODO: 後で修正", "HIGH", "担当者・コンテキストなしのTODOが検出されました"),
        ("暫定対応として実装", "HIGH", "バンドエイド修正の可能性が検出されました"),
        ("FIXME later", "HIGH", "担当者・コンテキストなしのFIXMEが検出されました"),
        
        # INFO パターン
        ("console.log('debug')", "INFO", "デバッグ用console.logが検出されました"),
        ("print('test debug')", "INFO", "デバッグ用print文が検出されました"),
        ("debugger;", "INFO", "JavaScriptデバッガ文が検出されました"),
        ("var oldCode = 'test';", "INFO", "JavaScript 'var'の使用が検出されました（let/constを使用してください）"),
        
        # NONE パターン（安全なコード）
        ("const result = calculateTotal(items);", "NONE", ""),
        ("function processData(input) { return input.filter(x => x > 0); }", "NONE", ""),
        ("let count = items.length;", "NONE", ""),
    ]
    
    # パフォーマンステスト
    print("📊 パフォーマンステスト")
    print("-" * 30)
    
    start_time = time.time()
    test_iterations = 1000
    
    for i in range(test_iterations):
        for test_input, expected_severity, expected_message in test_cases:
            severity, message, action = analyzer.analyze_input_optimized(test_input)
    
    end_time = time.time()
    total_time = (end_time - start_time) * 1000
    avg_time = total_time / (test_iterations * len(test_cases))
    
    print(f"総実行時間: {total_time:.2f}ms")
    print(f"平均実行時間: {avg_time:.4f}ms/回")
    print(f"処理能力: {int(1000/avg_time):,}回/秒")
    
    # 統計情報表示
    stats = analyzer.get_analysis_stats()
    optimizer_stats = stats['optimizer_stats']
    
    print(f"キャッシュヒット率: {optimizer_stats['cache_hit_rate']}")
    print(f"総クエリ数: {optimizer_stats['total_queries']}")
    print(f"パターンマッチ数: {optimizer_stats['pattern_matches']}")
    print()
    
    # 機能テスト
    print("🧪 機能テスト")
    print("-" * 30)
    
    passed = 0
    failed = 0
    
    for test_input, expected_severity, expected_message in test_cases:
        severity, message, action = analyzer.analyze_input_optimized(test_input)
        
        if severity == expected_severity:
            status = "✅ PASS"
            passed += 1
        else:
            status = f"❌ FAIL (期待: {expected_severity}, 実際: {severity})"
            failed += 1
        
        emoji = action.get('emoji', '❓')
        prefix = action.get('prefix', severity)
        
        print(f"{status}")
        print(f"  入力: {test_input[:50]}...")
        print(f"  結果: {emoji} {prefix} - {message}")
        print()
    
    # テスト結果サマリー
    print("📋 テスト結果サマリー")
    print("-" * 30)
    print(f"✅ 成功: {passed}件")
    print(f"❌ 失敗: {failed}件")
    print(f"📊 成功率: {(passed/(passed+failed)*100):.1f}%")
    
    # パフォーマンス制約チェック
    print("\n⏱️ パフォーマンス制約チェック")
    print("-" * 30)
    
    if avg_time < 1.0:  # 1ms未満
        print("✅ パフォーマンス: 優秀 (< 1ms/回)")
    elif avg_time < 5.0:  # 5ms未満
        print("✅ パフォーマンス: 良好 (< 5ms/回)")
    else:
        print("⚠️ パフォーマンス: 要改善 (> 5ms/回)")
    
    # 総合評価
    print("\n🎯 総合評価")
    print("-" * 30)
    
    if failed == 0 and avg_time < 5.0:
        print("🎉 Phase 2統合テスト: 完全成功")
        print("   すべての機能が正常に動作し、パフォーマンス要件を満たしています")
        return True
    elif failed == 0:
        print("⚠️ Phase 2統合テスト: 部分成功（パフォーマンス要改善）")
        return False
    else:
        print("❌ Phase 2統合テスト: 失敗")
        print(f"   {failed}件の機能テストが失敗しています")
        return False

if __name__ == "__main__":
    success = test_phase2_integration()
    sys.exit(0 if success else 1)
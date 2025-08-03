#!/usr/bin/env python3
"""
Lacuna Implementation Pattern Detection Test
実装困難時の機能低下・ラクナ実装パターン検出テスト

ユーザーフィードバック対応:
"実装の際、躓くと安易に機能低下させ、ラクナ実装をする傾向がある。"
"""

import sys
import os
import json
import re
from pathlib import Path

# プロジェクトルートに移動
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "scripts"))

try:
    from scripts.optimized_severity_analyzer import get_analyzer
except ImportError:
    # 直接パターンテストを実装
    def analyze_content_simple(content: str):
        """簡易パターンマッチング"""
        patterns_file = project_root / "config" / "patterns.json"
        
        if not patterns_file.exists():
            return None, None, {}
        
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns_config = json.load(f)
        
        # 各重要度レベルをチェック
        for severity in ['CRITICAL', 'HIGH', 'INFO']:
            if severity in patterns_config:
                for category, category_data in patterns_config[severity].items():
                    if 'patterns' in category_data:
                        for pattern_str, message in category_data['patterns'].items():
                            try:
                                if re.search(pattern_str, content, re.IGNORECASE):
                                    return pattern_str, message, {
                                        'severity': severity,
                                        'category': category
                                    }
                            except re.error:
                                continue
        
        return None, None, {}
    
    # ダミーアナライザー
    class DummyAnalyzer:
        def analyze_content(self, content):
            return analyze_content_simple(content)
    
    def get_analyzer():
        return DummyAnalyzer()

def test_lacuna_implementation_patterns():
    """ラクナ実装・機能低下パターンのテスト"""
    print("🚨 Lacuna Implementation Pattern Detection Test")
    print("=" * 70)
    
    analyzer = get_analyzer()
    
    # テストケース: 実装困難時のラクナ実装パターン
    test_cases = [
        # 機能削減パターン
        {
            "input": "# Lacuna implementation - reduced functionality due to complexity",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "明示的なラクナ実装宣言"
        },
        {
            "input": "// Quick fix implementation until we can solve the complex issue",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "複雑問題の一時的回避"
        },
        {
            "input": "# Feature reduction due to implementation difficulty",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "実装困難による機能削減"
        },
        {
            "input": "# Temporary solution - disable advanced features for now",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "高度機能の一時無効化"
        },
        
        # 実装困難時の簡素化パターン
        {
            "input": "# Got stuck implementing complex algorithm, simplified approach",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "description": "アルゴリズム複雑化による簡素化"
        },
        {
            "input": "// Implementation too difficult, using simpler alternative",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "description": "実装困難による代替案採用"
        },
        {
            "input": "# Stumbled during implementation, switching to simple version",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "description": "実装途中での簡易版切り替え"
        },
        
        # 機能放棄・諦めパターン
        {
            "input": "# Give up advanced feature due to complexity",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "description": "複雑性による機能諦め"
        },
        {
            "input": "// Abandon this feature - too complex to implement",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "description": "実装複雑による機能放棄"
        },
        
        # 期限・外圧による機能削減
        {
            "input": "# Reduce scope due to tight deadline constraints",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "description": "期限制約による機能削減"
        },
        {
            "input": "// Cut features to meet deadline - implement later",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "description": "期限優先の機能カット"
        },
        
        # テスト無効化パターン
        {
            "input": "# Disable test - implementation too difficult to complete",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "実装困難によるテスト無効化"
        },
        {
            "input": "// Skip test until complex implementation is finished",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "複雑実装未完了によるテストスキップ"
        },
        
        # 品質低下パターン
        {
            "input": "# Lower quality implementation due to complexity",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "複雑性による品質低下実装"
        },
        {
            "input": "// Reduce quality standards to get something working",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation",
            "description": "動作優先の品質基準低下"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 ラクナテストケース {i}: {test_case['description']}")
        print(f"   📝 入力: {test_case['input'][:50]}...")
        
        # パターン分析実行
        pattern, message, metadata = analyzer.analyze_content(test_case['input'])
        
        if pattern:
            # メタデータから実際の重要度とカテゴリを取得
            actual_severity = metadata.get('severity', 'UNKNOWN')
            actual_category = metadata.get('category', 'unknown')
            
            print(f"   ✅ 検出成功:")
            print(f"      パターン: {pattern}")
            print(f"      メッセージ: {message}")
            print(f"      重要度: {actual_severity}")
            print(f"      カテゴリ: {actual_category}")
            
            # 期待値との比較
            severity_match = actual_severity == test_case['expected_severity']
            pattern_match = test_case['expected_pattern'] in actual_category
            
            if severity_match and pattern_match:
                print(f"      🎯 期待値一致")
            else:
                print(f"      ⚠️ 期待値不一致")
                print(f"         期待重要度: {test_case['expected_severity']} vs 実際: {actual_severity}")
                print(f"         期待パターン: {test_case['expected_pattern']} vs 実際: {actual_category}")
            
            results.append({
                'test_case': i,
                'detected': True,
                'severity_match': severity_match,
                'pattern_match': pattern_match,
                'description': test_case['description']
            })
        else:
            print(f"   ❌ 検出失敗: パターンが見つかりませんでした")
            print(f"      期待: {test_case['expected_pattern']} / {test_case['expected_severity']}")
            results.append({
                'test_case': i,
                'detected': False,
                'severity_match': False,
                'pattern_match': False,
                'description': test_case['description']
            })
    
    # 結果サマリー
    print(f"\n📊 ラクナ実装パターンテスト結果サマリー")
    print("=" * 60)
    
    detected_count = sum(1 for r in results if r['detected'])
    severity_match_count = sum(1 for r in results if r['severity_match'])
    pattern_match_count = sum(1 for r in results if r['pattern_match'])
    
    total_tests = len(test_cases)
    
    print(f"総テスト数: {total_tests}")
    print(f"検出成功: {detected_count} ({detected_count/total_tests*100:.1f}%)")
    print(f"重要度一致: {severity_match_count} ({severity_match_count/total_tests*100:.1f}%)")
    print(f"パターン一致: {pattern_match_count} ({pattern_match_count/total_tests*100:.1f}%)")
    
    # カテゴリ別統計
    print(f"\n📈 パターンカテゴリ別検出結果:")
    category_stats = {
        'incomplete_implementation': {'total': 0, 'detected': 0},
        'bandaid_fixes': {'total': 0, 'detected': 0}
    }
    
    for i, test_case in enumerate(test_cases):
        expected_pattern = test_case['expected_pattern']
        if expected_pattern in category_stats:
            category_stats[expected_pattern]['total'] += 1
            if results[i]['detected'] and results[i]['pattern_match']:
                category_stats[expected_pattern]['detected'] += 1
    
    for category, stats in category_stats.items():
        if stats['total'] > 0:
            detection_rate = stats['detected'] / stats['total'] * 100
            print(f"   • {category}: {stats['detected']}/{stats['total']} ({detection_rate:.1f}%)")
    
    # 総合評価
    overall_score = (detected_count + severity_match_count + pattern_match_count) / (total_tests * 3) * 100
    print(f"\n🎯 ラクナ実装検出総合スコア: {overall_score:.1f}%")
    
    if overall_score >= 95:
        print("🏆 卓越: ラクナ実装・機能低下パターンの検出精度が卓越しています")
    elif overall_score >= 90:
        print("🥇 優秀: ラクナ実装・機能低下パターンの検出精度が優秀です")
    elif overall_score >= 80:
        print("✅ 良好: ラクナ実装・機能低下パターンの検出精度が良好です")
    elif overall_score >= 70:
        print("⚠️ 改善必要: 一部のラクナ実装パターンで検出精度が不足しています")
    else:
        print("❌ 要修正: ラクナ実装パターン検出精度が低すぎます")
    
    # 検出失敗ケース分析
    failed_cases = [r for r in results if not r['detected']]
    if failed_cases:
        print(f"\n🔍 検出失敗ケース分析:")
        for failed in failed_cases:
            print(f"   • ケース{failed['test_case']}: {failed['description']}")
        print(f"   → patterns.jsonに追加パターンが必要の可能性")
    
    # 実用性評価
    practical_cases = [r for r in results if r['detected'] and r['pattern_match']]
    practical_rate = len(practical_cases) / total_tests * 100
    print(f"\n💼 実用性評価: {practical_rate:.1f}%")
    
    if practical_rate >= 85:
        print("   ✅ 実用レベル: Claude Codeのラクナ実装傾向を効果的に検出可能")
    else:
        print("   ⚠️ 改善必要: より多くのラクナ実装パターンの追加が必要")
    
    return overall_score

if __name__ == "__main__":
    score = test_lacuna_implementation_patterns()
    sys.exit(0 if score >= 80 else 1)
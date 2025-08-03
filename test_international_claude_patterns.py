#!/usr/bin/env python3
"""
Claude Code国際事例エラーパターンのテスト
海外Reddit・GitHub・Stack Overflowから収集した最新パターン検証
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

def test_international_claude_patterns():
    """国際的なClaude Code特有パターンのテスト"""
    print("🌍 Claude Code国際事例エラーパターンテスト開始")
    print("=" * 70)
    
    analyzer = get_analyzer()
    
    # テストケース: 海外事例に基づく
    test_cases = [
        # 新しいClaude Code特有エラー（2024-2025海外報告）
        {
            "input": "503 Service Unavailable - Claude Code API",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors",
            "source": "Reddit r/ClaudeAI"
        },
        {
            "input": "Invalid API key for Claude authentication",
            "expected_severity": "CRITICAL", 
            "expected_pattern": "claude_code_errors",
            "source": "GitHub issues"
        },
        {
            "input": "Context window full - please use /clear or /compact",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors", 
            "source": "Claude Code documentation"
        },
        {
            "input": "JavaScript heap out of memory during build",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors",
            "source": "Stack Overflow discussions"
        },
        {
            "input": "TypeError: Cannot read property 'map' of undefined",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors",
            "source": "Reddit programming discussions"
        },
        {
            "input": "Credit balance too low to continue session",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors",
            "source": "Claude Code user reports"
        },
        {
            "input": "Tests are green-washing - claiming to pass without running",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors",
            "source": "GitHub issue #1501"
        },
        
        # コンテキスト管理問題（新カテゴリ）
        {
            "input": "Claude seems to have context amnesia after compaction",
            "expected_severity": "HIGH",
            "expected_pattern": "context_management",
            "source": "Dolthub blog 2025"
        },
        {
            "input": "Auto-compaction broke the session continuity",
            "expected_severity": "HIGH",
            "expected_pattern": "context_management",
            "source": "GitHub issue #1436"
        },
        {
            "input": "Claude is re-introducing bugs we fixed earlier",
            "expected_severity": "HIGH",
            "expected_pattern": "context_management",
            "source": "Reddit programming"
        },
        {
            "input": "CLAUDE.md instructions being ignored completely",
            "expected_severity": "HIGH", 
            "expected_pattern": "context_management",
            "source": "GitHub issue #668"
        },
        {
            "input": "Tests claim to pass but they never actually ran",
            "expected_severity": "HIGH",
            "expected_pattern": "context_management",
            "source": "Reddit r/ClaudeAI"
        },
        {
            "input": "Claude hallucinated a reference to non-existent library",
            "expected_severity": "HIGH",
            "expected_pattern": "context_management",
            "source": "Academic discussions"
        },
        
        # 言語混在問題（海外報告）
        {
            "input": "Mixed Lua and JavaScript syntax in single file",
            "expected_severity": "HIGH",
            "expected_pattern": "bandaid_fixes",
            "source": "Reddit language-mixing report"
        },
        
        # シェル関連問題
        {
            "input": "Z-shell aliases break bash commands - parse error near ()",
            "expected_severity": "HIGH",
            "expected_pattern": "git_issues",
            "source": "GitHub issue #783"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 国際テストケース {i}: {test_case['input'][:60]}...")
        print(f"   📍 出典: {test_case['source']}")
        
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
                'source': test_case['source']
            })
        else:
            print(f"   ❌ 検出失敗: パターンが見つかりませんでした")
            print(f"      期待: {test_case['expected_pattern']} / {test_case['expected_severity']}")
            results.append({
                'test_case': i,
                'detected': False,
                'severity_match': False,
                'pattern_match': False,
                'source': test_case['source']
            })
    
    # 結果サマリー
    print(f"\n📊 国際事例テスト結果サマリー")
    print("=" * 50)
    
    detected_count = sum(1 for r in results if r['detected'])
    severity_match_count = sum(1 for r in results if r['severity_match'])
    pattern_match_count = sum(1 for r in results if r['pattern_match'])
    
    total_tests = len(test_cases)
    
    print(f"総テスト数: {total_tests}")
    print(f"検出成功: {detected_count} ({detected_count/total_tests*100:.1f}%)")
    print(f"重要度一致: {severity_match_count} ({severity_match_count/total_tests*100:.1f}%)")
    print(f"パターン一致: {pattern_match_count} ({pattern_match_count/total_tests*100:.1f}%)")
    
    # ソース別統計
    print(f"\n📈 情報源別検出結果:")
    source_stats = {}
    for result in results:
        source = result['source']
        if source not in source_stats:
            source_stats[source] = {'total': 0, 'detected': 0}
        source_stats[source]['total'] += 1
        if result['detected']:
            source_stats[source]['detected'] += 1
    
    for source, stats in source_stats.items():
        detection_rate = stats['detected'] / stats['total'] * 100
        print(f"   • {source}: {stats['detected']}/{stats['total']} ({detection_rate:.1f}%)")
    
    # 総合評価
    overall_score = (detected_count + severity_match_count + pattern_match_count) / (total_tests * 3) * 100
    print(f"\n🎯 国際事例総合スコア: {overall_score:.1f}%")
    
    if overall_score >= 95:
        print("🏆 卓越: 国際的なClaude Code特有パターンの検出精度が卓越しています")
    elif overall_score >= 90:
        print("🥇 優秀: 国際的なClaude Code特有パターンの検出精度が優秀です")
    elif overall_score >= 80:
        print("✅ 良好: 国際的なClaude Code特有パターンの検出精度が良好です")
    elif overall_score >= 70:
        print("⚠️ 改善必要: 一部の国際パターンで検出精度が不足しています")
    else:
        print("❌ 要修正: 国際パターン検出精度が低すぎます")
    
    # 新パターン検出成功率
    new_patterns_count = sum(1 for r in results[:7] if r['detected'])  # 最初の7つが新パターン
    new_patterns_rate = new_patterns_count / 7 * 100
    print(f"\n🌟 新規パターン検出率: {new_patterns_rate:.1f}% ({new_patterns_count}/7)")
    
    return overall_score

if __name__ == "__main__":
    score = test_international_claude_patterns()
    sys.exit(0 if score >= 85 else 1)
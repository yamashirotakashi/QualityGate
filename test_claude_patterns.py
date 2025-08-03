#!/usr/bin/env python3
"""
Claude Code特有エラーパターンのテスト
実際のユーザー報告に基づくパターン検証
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

def test_claude_code_patterns():
    """Claude Code特有パターンのテスト"""
    print("🧪 Claude Code特有エラーパターンテスト開始")
    print("=" * 60)
    
    analyzer = get_analyzer()
    
    # テストケース: 実際のエラーメッセージに基づく
    test_cases = [
        # ファイル関連エラー
        {
            "input": "FileNotFoundError: [Errno 2] No such file or directory: '/path/to/file'",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors"
        },
        {
            "input": "Permission denied: '/usr/local/bin/script.py'",
            "expected_severity": "CRITICAL", 
            "expected_pattern": "claude_code_errors"
        },
        
        # Git関連エラー  
        {
            "input": "fatal: not a git repository (or any of the parent directories): .git",
            "expected_severity": "HIGH",
            "expected_pattern": "git_issues"
        },
        {
            "input": "fatal: Authentication failed for 'https://github.com/user/repo.git'",
            "expected_severity": "HIGH",
            "expected_pattern": "git_issues"
        },
        {
            "input": "CONFLICT (content): Merge conflict in src/main.py",
            "expected_severity": "HIGH",
            "expected_pattern": "git_issues"
        },
        
        # 依存関係エラー
        {
            "input": "ModuleNotFoundError: No module named 'requests'",
            "expected_severity": "HIGH",
            "expected_pattern": "dependency_issues"
        },
        {
            "input": "ImportError: cannot import name 'deprecated_function' from 'old_module'",
            "expected_severity": "HIGH", 
            "expected_pattern": "dependency_issues"
        },
        {
            "input": "npm ERR! 404 '@unknown/package' is not in this registry",
            "expected_severity": "HIGH",
            "expected_pattern": "dependency_issues"
        },
        
        # メモリ・クラッシュエラー
        {
            "input": "FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors"
        },
        {
            "input": "Segmentation fault (core dumped)",
            "expected_severity": "CRITICAL",
            "expected_pattern": "claude_code_errors"
        },
        
        # 未実装パターン
        {
            "input": "raise NotImplementedError('This method needs implementation')",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation"
        },
        {
            "input": "return None # stub implementation",
            "expected_severity": "HIGH",
            "expected_pattern": "incomplete_implementation"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 テストケース {i}: {test_case['input'][:50]}...")
        
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
                'pattern_match': pattern_match
            })
        else:
            print(f"   ❌ 検出失敗: パターンが見つかりませんでした")
            results.append({
                'test_case': i,
                'detected': False,
                'severity_match': False,
                'pattern_match': False
            })
    
    # 結果サマリー
    print(f"\n📊 テスト結果サマリー")
    print("=" * 40)
    
    detected_count = sum(1 for r in results if r['detected'])
    severity_match_count = sum(1 for r in results if r['severity_match'])
    pattern_match_count = sum(1 for r in results if r['pattern_match'])
    
    total_tests = len(test_cases)
    
    print(f"総テスト数: {total_tests}")
    print(f"検出成功: {detected_count} ({detected_count/total_tests*100:.1f}%)")
    print(f"重要度一致: {severity_match_count} ({severity_match_count/total_tests*100:.1f}%)")
    print(f"パターン一致: {pattern_match_count} ({pattern_match_count/total_tests*100:.1f}%)")
    
    # 総合評価
    overall_score = (detected_count + severity_match_count + pattern_match_count) / (total_tests * 3) * 100
    print(f"\n🎯 総合スコア: {overall_score:.1f}%")
    
    if overall_score >= 90:
        print("🏆 優秀: Claude Code特有パターンの検出精度が非常に高いです")
    elif overall_score >= 80:
        print("✅ 良好: Claude Code特有パターンの検出精度が良好です")
    elif overall_score >= 70:
        print("⚠️ 改善必要: 一部のパターンで検出精度が不足しています")
    else:
        print("❌ 要修正: パターン検出精度が低すぎます")
    
    return overall_score

if __name__ == "__main__":
    score = test_claude_code_patterns()
    sys.exit(0 if score >= 80 else 1)
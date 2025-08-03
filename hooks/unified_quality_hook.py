#!/usr/bin/env python3
"""
QualityGate Phase 2 - 統合品質Hook
既存design_protection_hookとQualityGateを統合した最適化システム
"""

import sys
import os
import re
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# QualityGate 最適化Severity Analyzerをインポート
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')
from optimized_severity_analyzer import OptimizedSeverityAnalyzer

# 設計思想保護フレームワーク用設定
DESIGN_CONFIG_PATH = Path("/mnt/c/Users/tky99/dev/.claude_quality_hooks.json")
PRE_FIX_ANALYZER = Path("/mnt/c/Users/tky99/dev/scripts/pre_fix_analyzer.py")
BUG_FIX_ANALYZER = Path("/mnt/c/Users/tky99/dev/scripts/bug_fix_analyzer.py")

class UnifiedQualityHook:
    """統合品質Hook - QualityGate + 設計思想保護フレームワーク"""
    
    def __init__(self):
        self.analyzer = OptimizedSeverityAnalyzer()
        self.start_time = time.time()
        
    def load_design_config(self) -> Dict:
        """設計思想保護フレームワークの設定を読み込む"""
        if DESIGN_CONFIG_PATH.exists():
            try:
                with open(DESIGN_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def should_run_design_analysis(self, command: str, message: str = "") -> bool:
        """設計思想保護分析が必要かチェック"""
        config = self.load_design_config()
        if not config.get("bugfix_protection", {}).get("enabled", True):
            return False
        
        triggers = config.get("bugfix_protection", {}).get("triggers", {})
        keywords = triggers.get("keywords", [])
        patterns = triggers.get("regex_patterns", [])
        
        # コマンドとメッセージを結合してチェック
        full_text = f"{command} {message}".lower()
        
        # キーワードチェック
        for keyword in keywords:
            if keyword.lower() in full_text:
                return True
                
        # 正規表現チェック
        for pattern in patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                return True
                
        return False
    
    def run_design_analysis(self, command: str, message: str = "") -> None:
        """設計思想保護分析を実行（非ブロッキング）"""
        print("🔍 設計思想保護分析を自動実行中...", file=sys.stderr)
        
        # Pre-fix Analyzer実行（タイムアウト10秒）
        if PRE_FIX_ANALYZER.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(PRE_FIX_ANALYZER), message or command],
                    capture_output=True,
                    text=True,
                    timeout=10  # タイムアウト短縮
                )
                if result.stdout:
                    print(result.stdout, file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("⚠️  Pre-fix Analyzer: タイムアウト（10秒）", file=sys.stderr)
            except Exception as e:
                print(f"⚠️  Pre-fix Analyzer実行エラー: {e}", file=sys.stderr)
        
        # コミット関連の場合はBug Fix Analyzerも実行
        if any(cmd in command for cmd in ["git commit", "git push", "commit", "push"]):
            if BUG_FIX_ANALYZER.exists():
                try:
                    result = subprocess.run(
                        [sys.executable, str(BUG_FIX_ANALYZER), message or command],
                        capture_output=True,
                        text=True,
                        timeout=10  # タイムアウト短縮
                    )
                    if result.stdout:
                        print(result.stdout, file=sys.stderr)
                except subprocess.TimeoutExpired:
                    print("⚠️  Bug Fix Analyzer: タイムアウト（10秒）", file=sys.stderr)
                except Exception as e:
                    print(f"⚠️  Bug Fix Analyzer実行エラー: {e}", file=sys.stderr)
    
    def check_timeout_constraint(self) -> bool:
        """5秒制約チェック"""
        elapsed = time.time() - self.start_time
        return elapsed < 4.5  # 4.5秒でタイムアウト警告
    
    def process_input(self, input_text: str, operation_type: str = "general") -> int:
        """
        統合品質チェック処理
        
        Args:
            input_text: チェック対象のテキスト
            operation_type: 操作タイプ（edit/bash/general）
            
        Returns:
            0: 続行、2: ブロック
        """
        # バイパスチェック（最優先）
        if (os.environ.get("BYPASS_DESIGN_HOOK") == "1" or 
            os.environ.get("QUALITYGATE_DISABLED") == "1" or
            os.environ.get("EMERGENCY_BYPASS") == "1"):
            return 0
        
        try:
            # QualityGate品質分析（高速実行）
            severity, message, action = self.analyzer.analyze_input_optimized(input_text)
            
            # タイムアウトチェック
            if not self.check_timeout_constraint():
                print("⚠️  品質分析: タイムアウト制約により短縮実行", file=sys.stderr)
                return 0
            
            # CRITICAL違反の場合は即座にブロック
            if severity == "CRITICAL":
                emoji = action.get('emoji', '🚫')
                prefix = action.get('prefix', '重大')
                print(f"🔒 QualityGate {emoji} {prefix}: {message}", file=sys.stderr)
                print("🚫 QualityGate: 重大な品質違反により実行をブロックしました", file=sys.stderr)
                return 2
            
            # HIGH違反の場合は警告表示（非ブロッキング）
            elif severity == "HIGH":
                emoji = action.get('emoji', '⚠️')
                prefix = action.get('prefix', '警告')
                print(f"🔒 QualityGate {emoji} {prefix}: {message}", file=sys.stderr)
                if operation_type in ["edit", "bash"]:
                    print("⏱️  QualityGate: 2秒間停止しています...", file=sys.stderr)
                    time.sleep(2)
            
            # INFO違報の場合は軽微な表示
            elif severity == "INFO":
                emoji = action.get('emoji', 'ℹ️')
                prefix = action.get('prefix', '情報')
                print(f"🔒 QualityGate {emoji} {prefix}: {message}", file=sys.stderr)
            
            # タイムアウトチェック（設計思想保護分析前）
            if not self.check_timeout_constraint():
                return 0
            
            # 設計思想保護分析（時間に余裕がある場合のみ）
            if self.should_run_design_analysis(input_text):
                elapsed = time.time() - self.start_time
                if elapsed < 3.0:  # 3秒以内なら実行
                    self.run_design_analysis(input_text)
                else:
                    print("⚠️  設計思想保護分析: タイムアウト制約によりスキップ", file=sys.stderr)
            
            return 0
            
        except Exception as e:
            print(f"⚠️  統合品質Hook実行エラー: {e}", file=sys.stderr)
            return 0  # エラーでもブロックしない

def main():
    """メインエントリーポイント"""
    hook = UnifiedQualityHook()
    
    # コマンドライン引数から情報を取得
    input_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    # 環境変数から情報を取得（Hook経由）
    hook_command = os.environ.get("CLAUDE_HOOK_COMMAND", "")
    hook_message = os.environ.get("CLAUDE_HOOK_MESSAGE", "")
    
    # 実際の入力テキストを決定
    actual_input = input_text or hook_command or hook_message
    
    # 操作タイプを環境変数から取得
    operation_type = os.environ.get("QUALITYGATE_OPERATION_TYPE", "general")
    
    if actual_input:
        exit_code = hook.process_input(actual_input, operation_type)
        sys.exit(exit_code)
    else:
        # 入力がない場合は正常終了
        sys.exit(0)

if __name__ == "__main__":
    main()
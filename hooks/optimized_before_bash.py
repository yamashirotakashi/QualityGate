#!/usr/bin/env python3
"""
QualityGate Phase 2 - 最適化Bash Hook
高速・軽量なBash操作用品質チェック
"""

import sys
import os

# 統合Hookシステムをインポート
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/hooks')
from unified_quality_hook import UnifiedQualityHook

def main():
    """Bash操作用メインエントリーポイント"""
    # 操作タイプを環境変数に設定
    os.environ["QUALITYGATE_OPERATION_TYPE"] = "bash"
    
    hook = UnifiedQualityHook()
    
    # Bashコマンドを取得
    if len(sys.argv) > 1:
        bash_command = " ".join(sys.argv[1:])
    else:
        bash_command = ""
    
    # 環境変数からも情報を取得
    hook_command = os.environ.get("CLAUDE_HOOK_COMMAND", "")
    hook_message = os.environ.get("CLAUDE_HOOK_MESSAGE", "")
    
    # 実際のコマンドを決定
    actual_command = bash_command or hook_command or hook_message
    
    if actual_command:
        # コマンド表示（デバッグ用）
        display_command = actual_command[:100] + ('...' if len(actual_command) > 100 else '')
        print(f"🔍 コマンド: {display_command}", file=sys.stderr)
        
        # 統合品質チェック実行
        exit_code = hook.process_input(actual_command, "bash")
        sys.exit(exit_code)
    else:
        # コマンドがない場合は正常終了
        sys.exit(0)

if __name__ == "__main__":
    main()
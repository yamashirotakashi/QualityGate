#!/usr/bin/env python3
"""
QualityGate Phase 2 - 最適化Edit Hook
高速・軽量な編集操作用品質チェック
"""

import sys
import os

# 統合Hookシステムをインポート
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/hooks')
from unified_quality_hook import UnifiedQualityHook

def main():
    """編集操作用メインエントリーポイント"""
    # 操作タイプを環境変数に設定
    os.environ["QUALITYGATE_OPERATION_TYPE"] = "edit"
    
    hook = UnifiedQualityHook()
    
    # 編集内容を取得（コマンドライン引数またはstdin）
    if len(sys.argv) > 1:
        edit_content = " ".join(sys.argv[1:])
    else:
        try:
            edit_content = sys.stdin.read()
        except:
            edit_content = ""
    
    # 環境変数からも情報を取得
    hook_command = os.environ.get("CLAUDE_HOOK_COMMAND", "")
    hook_message = os.environ.get("CLAUDE_HOOK_MESSAGE", "")
    
    # 実際の編集内容を決定
    actual_content = edit_content or hook_command or hook_message
    
    if actual_content:
        # 統合品質チェック実行
        exit_code = hook.process_input(actual_content, "edit")
        sys.exit(exit_code)
    else:
        # 編集内容がない場合は正常終了
        sys.exit(0)

if __name__ == "__main__":
    main()
# QualityGate - 強制的品質ゲート実装プロジェクト

## 概要
Claude Codeの既存Hook Systemを活用し、バンドエイド修正・ハードコード値・設計思想違反を**強制的に阻止**する品質ゲートシステム。

## 技術的根拠
- **実装可能性**: 90%信頼度（Sequential Thinking + Expert Analysis確認済み）
- **基盤**: Claude Code Hook System - exit code 2 blocking
- **制約**: 5秒タイムアウト、MCP競合回避必須

## 特殊プロンプト
```bash
[QGate]           # プロジェクトに切り替え
[QG]              # 短縮形
[QGate] status    # 実装状況確認
[QGate] test      # 機能テスト
[QGate] phase     # フェーズ切り替え
```

## クイックスタート

### 1. プロジェクト切り替え
```bash
[QGate]  # 自動的にプロジェクトディレクトリに移動
```

### 2. 現在の状況確認
```bash
[QGate] status
```

### 3. テスト実行
```bash
[QGate] test
```

## 実装フェーズ
- **Phase 0**: 基盤整備 (完了)
- **Phase 1**: Criticalパターンブロッキング (次期)
- **Phase 2**: Hook統合最適化
- **Phase 3**: Highパターン拡張
- **Phase 4**: 本格運用
 
## 主要ファイル
- `QUALITYGATE_PROJECT.md` - 詳細な実装戦略
- `CLAUDE.md` - プロジェクト固有設定
- `scripts/design_protection_hook.py` - メイン実装
- `config/patterns.json` - 検出ルール

## Codex 連携（前処理ランナー）
- 概要: Codex 側から編集/コマンド実行の直前に QualityGate を安全に呼び出すための軽量CLIを用意（CC設定は変更不要）。
- ランナー: `qualitygate/scripts/qg_runner.py`
- ルート: `QUALITYGATE_ROOT` を指定可能（未指定時はスクリプト相対で自動解決）。

使用例:
- 編集内容のチェック（`CRITICAL`で rc=2, ブロック）
  - `echo "<patch lines>" | python qualitygate/scripts/qg_runner.py --mode edit --source stdin`
- Bash コマンドのチェック
  - `echo "rm -rf /" | python qualitygate/scripts/qg_runner.py --mode bash --source stdin`
- 警告のみ（強制通過）
  - `... qg_runner.py --warn-only ...`

テスト（Codex向け追加分）:
- `python -m pytest -q qualitygate/tests/test_qg_runner_cli.py qualitygate/tests/integration/test_qualitygate_bridge_env.py`

備考:
- 緊急時バイパス: `export BYPASS_DESIGN_HOOK=1`（従来通り）。
- CC ブリッジは後方互換のまま、環境変数注入と rc=2 ブロック扱いに対応済み。

## 緊急時対応
```bash
export BYPASS_DESIGN_HOOK=1  # 一時無効化
```

詳細は `QUALITYGATE_PROJECT.md` を参照してください。

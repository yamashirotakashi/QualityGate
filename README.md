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

## 緊急時対応
```bash
export BYPASS_DESIGN_HOOK=1  # 一時無効化
```

詳細は `QUALITYGATE_PROJECT.md` を参照してください。
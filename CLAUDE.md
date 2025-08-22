# QualityGate プロジェクト固有設定
# グローバルルールの継承
@../CLAUDE.md

## 🔧 QualityGate固有の設定

### プロジェクト基本情報
- **プロジェクト名**: QualityGate
- **短縮名**: QG
- **特殊プロンプト**: [QGate], [QG]
- **目的**: Claude Codeにおける強制的品質ゲートの実装

### 開発環境設定
```bash
# プロジェクトディレクトリ
cd /mnt/c/Users/tky99/dev/qualitygate

# 関連スクリプト
/mnt/c/Users/tky99/dev/scripts/design_protection_hook.py
/mnt/c/Users/tky99/dev/.claude_hooks_config_optimized.json
/mnt/c/Users/tky99/dev/.bashrc.d/design_protection.sh
```

### 特殊プロンプト機能
```
[QGate]           # プロジェクトに切り替え + 状況確認
[QG]              # 短縮形
[QGate] status    # 実装フェーズ状況表示
[QGate] test      # ブロッキング機能テスト
[QGate] config    # Hook設定確認・変更
[QGate] bypass    # 緊急バイパス機能
[QGate] stats     # 効果測定・統計表示
[QGate] phase     # フェーズ切り替え
[QGate] rollback  # 前フェーズに戻る
```

### 実装フェーズ管理
- **Phase 0**: 基盤整備 (設計・計画)
- **Phase 1**: 軽量実装 (Critical patterns)
- **Phase 2**: Hook統合最適化
- **Phase 3**: 拡張実装 (High patterns)
- **Phase 4**: 本格運用

### セーフティ機能
```bash
# 緊急バイパス（環境変数）
export BYPASS_DESIGN_HOOK=1

# 一時無効化
export QUALITYGATE_DISABLED=1

# 警告のみモード
export QUALITYGATE_WARN_ONLY=1
```

### テストコマンド
```bash
# 基本機能テスト
python /mnt/c/Users/tky99/dev/scripts/design_protection_hook.py test

# Hook統合テスト
bash -c "echo 'とりあえず修正' | python design_protection_hook.py"

# パフォーマンステスト
time python design_protection_hook.py --performance-test
```

### ログ・監視
```bash
# ログ確認
tail -f /tmp/qualitygate.log

# 統計情報
python scripts/qualitygate_stats.py

# Hook実行状況
grep "QualityGate" ~/.claude/logs/*.log
```

### 作業フロー
1. `[QGate]` でプロジェクト切り替え
2. フェーズ状況確認
3. 実装・テスト・検証
4. フェーズ進行の判断
5. 効果測定とフィードバック収集

### 重要ファイル
- `QUALITYGATE_PROJECT.md` - プロジェクト憲章
- `handover.md` - セッション継続・作業引き継ぎ情報 ⭐ **必読**
- `TDD_GUARDIAN_DESIGN.md` - TDD Guardian System設計書
- `scripts/design_protection_hook.py` - 改修対象メインスクリプト
- `hooks/` - Hook統合スクリプト群
- `tests/` - テストスイート
- `docs/` - 詳細ドキュメント

### 品質目標
- ハードコード値コミット: 90%減少
- セキュリティ関連CR指摘: 70%減少
- 開発速度影響: 5%以内
- 開発者満足度: 8/10以上

## 🚨 緊急時対応
品質ゲートが開発を阻害する場合：
1. `export BYPASS_DESIGN_HOOK=1` で一時回避
2. 問題をIssue登録
3. フェーズ rollback検討
4. チーム合意による設定調整

## 📋 プロジェクト構造
```
/mnt/c/Users/tky99/dev/qualitygate/
├── CLAUDE.md                    # 本ファイル
├── QUALITYGATE_PROJECT.md       # プロジェクト憲章
├── README.md                    # 基本説明
├── scripts/                     # 実装スクリプト
│   ├── design_protection_hook.py  # メインスクリプト
│   ├── qualitygate_stats.py      # 統計収集
│   └── phase_manager.py          # フェーズ管理
├── hooks/                       # Hook統合
│   ├── before_edit.py           # 編集前Hook
│   └── before_bash.py           # Bash実行前Hook
├── tests/                       # テストスイート
│   ├── test_blocking.py         # ブロッキング機能テスト
│   └── test_performance.py     # パフォーマンステスト
├── docs/                        # ドキュメント
│   ├── implementation.md        # 実装詳細
│   └── patterns.md             # 検出パターン集
└── config/                      # 設定ファイル
    ├── patterns.json           # 検出ルール
    └── phases.json             # フェーズ設定
```
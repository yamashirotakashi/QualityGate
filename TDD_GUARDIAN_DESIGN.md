# TDD Guardian System 設計書

## 概要
TDD Guardian Systemは、QualityGateプロジェクトの拡張機能として、TDD（Test-Driven Development）プラクティスの適切な実施を支援・強制するシステムです。

## 設計思想

### 基本原則
1. **TDD哲学との整合性**: Red→Green→Refactorサイクルを尊重
2. **リファクタリング欠如の検出**: 不正実装ではなく、プロセスの欠如を検出
3. **段階的導入**: advisory mode → soft block → hard block

### 重要な洞察（Sequential Thinking分析より）
- TDDの「最小限の実装」（Fake it）は正当なプラクティス
- 問題は「リファクタリングフェーズの省略」
- 誤検出リスクの最小化が成功の鍵

## アーキテクチャ

### システム構成
```
┌─────────────────┐
│ [TDDQG] Prompt  │ ─┐ 手動起動
└─────────────────┘  │
                     ▼
┌─────────────────┐  ┌──────────────────────┐
│ Test-subagent   │──│ TDD Guardian Core    │
└─────────────────┘  │ ├──────────────────┤ │
                     │ │ Stage Tracker    │ │
┌─────────────────┐  │ │ Time Evaluator   │ │
│ CI/CD Pipeline  │──│ │ Config Manager   │ │
└─────────────────┘  │ │ Report Generator │ │
                     └──────────────────────┘
                              │
                     ┌────────▼────────┐
                     │ QualityGate     │
                     │ Hook System     │
                     └─────────────────┘
```

## 実装フェーズ

### Phase 0.5: セキュリティ修正（現在）
**期間**: 24-48時間  
**優先度**: 🔴 CRITICAL

#### タスク
1. JWTデフォルトシークレット修正
2. CORS設定のホワイトリスト化
3. SQLインジェクション対策

### Phase 1: TDDステージ追跡（2週間）
**期間**: 2週間  
**優先度**: 🟠 HIGH

#### コンポーネント実装

##### 1. TDDStageTracker
```python
class TDDStageTracker:
    """TDDサイクルの追跡と分析"""
    
    def __init__(self, repo_path: str):
        self.repo = git.Repo(repo_path)
        self.cache = {}
    
    def track_commit(self, commit_hash: str) -> TDDStage:
        """コミットからTDDステージを判定"""
        commit = self.repo.commit(commit_hash)
        
        # テストファイルの変更を検出
        if self._has_test_changes(commit):
            if self._tests_are_failing(commit):
                return TDDStage.RED
            else:
                return TDDStage.GREEN
        
        # 実装ファイルの変更を検出
        if self._has_implementation_changes(commit):
            if self._is_refactoring(commit):
                return TDDStage.REFACTOR
            else:
                return TDDStage.GREEN
        
        return TDDStage.UNKNOWN
    
    def detect_missing_refactor(self, 
                               branch: str = 'main',
                               threshold_hours: int = 48) -> List[Issue]:
        """リファクタリング欠如を検出"""
        issues = []
        green_commits = self._find_green_commits(branch)
        
        for commit in green_commits:
            time_since = datetime.now() - commit.committed_datetime
            if time_since.total_seconds() / 3600 > threshold_hours:
                if not self._has_subsequent_refactor(commit):
                    issues.append(RefactorMissingIssue(
                        commit=commit,
                        age_hours=time_since.total_seconds() / 3600
                    ))
        
        return issues
```

##### 2. 設定ファイル仕様
```yaml
# .tddguardian.yml
version: 1.0
mode: advisory  # advisory | warning | blocking

rules:
  refactor_deadline: 48h  # GREEN後のリファクタリング猶予期間
  
  exclude_patterns:
    - "*/config/*"      # 設定ファイルは除外
    - "*/constants/*"   # 定数定義は除外
    - "*_test.py"       # テストファイル自体は除外
  
  stage_detection:
    test_patterns:
      - "*_test.py"
      - "test_*.py"
      - "*/tests/*"
    
    refactor_indicators:
      - "rename"
      - "extract"
      - "simplify"
      - "clean"
      - "refactor"

performance:
  max_execution_time: 1.5ms  # パフォーマンス制約
  cache_ttl: 3600  # キャッシュ有効期限（秒）

reporting:
  format: json  # json | markdown | html
  verbosity: normal  # quiet | normal | verbose
```

### Phase 2: 時間ベース評価（1週間）
**期間**: 1週間  
**優先度**: 🟡 MEDIUM

#### 実装内容
- 時間経過に基づく警告レベルの段階的上昇
- プロジェクト固有の閾値設定
- 統計情報の収集と分析

### Phase 3: 高度な検出（オプション）
**期間**: 未定  
**優先度**: 🔵 LOW

#### 検討項目
- Mutation Testing統合（別システムとして）
- Property-based Testing推奨
- AI支援による意図分析

## パフォーマンス考慮事項

### 制約
- 全体処理時間: 1.5ms以内
- Hook実行時間: 0.05ms以内
- メモリ使用量: 50MB以下

### 最適化戦略
1. **差分駆動**: 変更ファイルのみ解析
2. **キャッシング**: git履歴のキャッシュ
3. **非同期処理**: 重い処理はバックグラウンド実行
4. **段階的実行**: 軽量チェック → 詳細分析

## セキュリティ考慮事項

### 既知の脆弱性（要修正）
1. JWTデフォルトシークレット
2. CORS設定の過度な許可
3. SQLインジェクション脆弱性

### 対策
- 環境変数の必須化
- ホワイトリスト方式の採用
- パラメータ化クエリの使用

## 成功指標

### KPI
- リファクタリング実施率: 80%以上
- 誤検出率: 10%以下
- パフォーマンス影響: 5%以内
- 開発者満足度: 7/10以上

### 測定方法
- git履歴の自動分析
- 開発者フィードバックの収集
- CI/CDパイプラインのメトリクス

## リスクと対策

### リスク
1. **誤検出による開発者の信頼喪失**
   - 対策: advisory modeから開始、段階的強化
   
2. **パフォーマンス劣化**
   - 対策: 差分駆動、キャッシング、非同期処理
   
3. **TDD哲学との矛盾**
   - 対策: リファクタリング欠如のみ検出

## 次のアクション

1. **即座実行（24-48時間）**
   - [ ] セキュリティ脆弱性修正
   - [ ] 修正の検証とテスト

2. **Phase 1開始準備**
   - [ ] git履歴解析ライブラリの選定
   - [ ] プロトタイプ実装
   - [ ] パフォーマンステスト

3. **ドキュメント整備**
   - [ ] ユーザーガイド作成
   - [ ] API仕様書作成
   - [ ] トラブルシューティングガイド

---

**作成日**: 2025-08-22  
**作成者**: QualityGateチーム  
**バージョン**: 1.0.0
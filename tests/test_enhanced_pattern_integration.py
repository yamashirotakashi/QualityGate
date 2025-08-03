#!/usr/bin/env python3
"""
QualityGate Phase 3A Week 2 - 統合パターン検出テスト
AST分析器と強化パターン検出器の統合検証
"""

import sys
import json
import time
from pathlib import Path

# qualitygate scriptsをパスに追加
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')

from ast_project_analyzer import ASTProjectAnalyzer
from enhanced_pattern_detector import EnhancedPatternDetector, PatternType

class IntegratedPatternTester:
    """統合パターン検出テスター"""
    
    def __init__(self):
        self.project_path = "/mnt/c/Users/tky99/dev/qualitygate"
        self.ast_analyzer = ASTProjectAnalyzer(self.project_path)
        self.enhanced_detector = EnhancedPatternDetector(self.project_path)
        
        # テスト用ターゲット指標
        self.target_metrics = {
            'pattern_detection_accuracy': 0.85,  # 85%以上
            'rule_generation_accuracy': 0.80,    # 80%以上
            'adaptation_time_seconds': 3.0       # 3秒以下
        }
    
    def test_integration_workflow(self) -> dict:
        """統合ワークフローテスト"""
        print("🔧 統合ワークフローテスト開始...")
        start_time = time.time()
        
        # Step 1: AST分析実行
        print("  📊 AST分析実行...")
        self.ast_analyzer.analyze_project_async()
        
        # 分析完了まで待機
        while self.ast_analyzer.is_analyzing:
            time.sleep(0.5)
        
        result = self.ast_analyzer.get_analysis_result()
        if not result:
            return {'status': 'FAILED', 'reason': 'AST分析が失敗しました'}
        
        # Step 2: 強化パターン検出
        print("  🔍 強化パターン検出実行...")
        file_results = list(result.file_analysis_results.values())
        enhanced_patterns = self.enhanced_detector.enhance_pattern_detection(file_results)
        
        # Step 3: プロジェクト固有ルール生成
        print("  📋 プロジェクト固有ルール生成...")
        project_rules = self.enhanced_detector.generate_project_specific_rules()
        
        end_time = time.time()
        adaptation_time = end_time - start_time
        
        return {
            'status': 'SUCCESS',
            'adaptation_time': adaptation_time,
            'detected_patterns': len(enhanced_patterns),
            'generated_rules': len(project_rules),
            'file_analysis_count': len(file_results),
            'patterns': enhanced_patterns,
            'rules': project_rules,
            'project_profile': self.enhanced_detector.project_profile
        }
    
    def test_pattern_accuracy(self, workflow_result: dict) -> dict:
        """パターン検出精度テスト"""
        print("📊 パターン検出精度テスト...")
        
        patterns = workflow_result['patterns']
        
        # 期待されるパターンタイプ（より包括的に）
        expected_pattern_types = {
            PatternType.NAMING_CONVENTION,
            PatternType.IMPORT_STYLE,
            PatternType.CODE_STRUCTURE,
            PatternType.ERROR_HANDLING,
            PatternType.DOCUMENTATION
        }
        
        detected_pattern_types = {pattern.pattern_type for pattern in patterns}
        
        # 精度計算
        type_coverage = len(detected_pattern_types & expected_pattern_types) / len(expected_pattern_types)
        
        # 信頼度分析
        high_confidence_patterns = [p for p in patterns if p.confidence_score >= 0.8]
        confidence_rate = len(high_confidence_patterns) / len(patterns) if patterns else 0
        
        # 総合精度スコア
        overall_accuracy = (type_coverage + confidence_rate) / 2
        
        return {
            'pattern_type_coverage': type_coverage,
            'high_confidence_rate': confidence_rate,
            'overall_accuracy': overall_accuracy,
            'detected_types': [t.value for t in detected_pattern_types],
            'high_confidence_count': len(high_confidence_patterns)
        }
    
    def test_rule_generation_accuracy(self, workflow_result: dict) -> dict:
        """ルール生成精度テスト"""
        print("📋 ルール生成精度テスト...")
        
        rules = workflow_result['rules']
        
        # 期待されるルール属性
        required_fields = ['pattern_id', 'severity', 'pattern', 'message', 'category']
        
        valid_rules = []
        for rule in rules:
            if all(field in rule for field in required_fields):
                if rule['confidence'] >= 0.8:  # 高信頼度ルール
                    valid_rules.append(rule)
        
        rule_validity_rate = len(valid_rules) / len(rules) if rules else 0
        
        # セキュリティとコード品質に関するルールの検証
        security_rules = [r for r in valid_rules if 'security' in r['category'].lower()]
        quality_rules = [r for r in valid_rules if 'naming' in r['category'].lower()]
        
        return {
            'rule_validity_rate': rule_validity_rate,
            'valid_rules_count': len(valid_rules),
            'security_rules_count': len(security_rules),
            'quality_rules_count': len(quality_rules),
            'total_rules_generated': len(rules)
        }
    
    def test_performance_targets(self, workflow_result: dict, accuracy_result: dict, rule_result: dict) -> dict:
        """パフォーマンス目標達成テスト"""
        print("🎯 パフォーマンス目標達成テスト...")
        
        results = {
            'pattern_detection_accuracy': {
                'target': self.target_metrics['pattern_detection_accuracy'],
                'actual': accuracy_result['overall_accuracy'],
                'passed': accuracy_result['overall_accuracy'] >= self.target_metrics['pattern_detection_accuracy']
            },
            'rule_generation_accuracy': {
                'target': self.target_metrics['rule_generation_accuracy'],
                'actual': rule_result['rule_validity_rate'],
                'passed': rule_result['rule_validity_rate'] >= self.target_metrics['rule_generation_accuracy']
            },
            'adaptation_time': {
                'target': self.target_metrics['adaptation_time_seconds'],
                'actual': workflow_result['adaptation_time'],
                'passed': workflow_result['adaptation_time'] <= self.target_metrics['adaptation_time_seconds']
            }
        }
        
        all_passed = all(result['passed'] for result in results.values())
        
        return {
            'all_targets_met': all_passed,
            'individual_results': results
        }
    
    def generate_integration_report(self) -> dict:
        """統合テストレポート生成"""
        print("📄 統合テストレポート生成...")
        
        # 統合ワークフローテスト
        workflow_result = self.test_integration_workflow()
        if workflow_result['status'] != 'SUCCESS':
            return workflow_result
        
        # 精度テスト
        accuracy_result = self.test_pattern_accuracy(workflow_result)
        rule_result = self.test_rule_generation_accuracy(workflow_result)
        performance_result = self.test_performance_targets(workflow_result, accuracy_result, rule_result)
        
        return {
            'test_timestamp': time.time(),
            'overall_status': 'PASSED' if performance_result['all_targets_met'] else 'FAILED',
            'workflow': workflow_result,
            'pattern_accuracy': accuracy_result,
            'rule_generation': rule_result,
            'performance_validation': performance_result,
            'project_profile': workflow_result.get('project_profile')
        }

def main():
    """統合パターン検出テスト実行"""
    print("🚀 QualityGate Phase 3A Week 2 統合テスト開始")
    print("=" * 60)
    
    tester = IntegratedPatternTester()
    
    # 統合テスト実行
    report = tester.generate_integration_report()
    
    # 結果表示
    print("\n📋 統合テスト結果サマリー")
    print("-" * 40)
    
    print(f"📊 総合ステータス: {report['overall_status']}")
    
    if report['overall_status'] == 'PASSED':
        workflow = report['workflow']
        accuracy = report['pattern_accuracy']
        rules = report['rule_generation']
        performance = report['performance_validation']
        
        print(f"\n🔧 ワークフロー結果:")
        print(f"  適応時間: {workflow['adaptation_time']:.2f}秒")
        print(f"  検出パターン数: {workflow['detected_patterns']}")
        print(f"  生成ルール数: {workflow['generated_rules']}")
        print(f"  分析ファイル数: {workflow['file_analysis_count']}")
        
        print(f"\n📊 パターン検出精度:")
        print(f"  パターンタイプカバレッジ: {accuracy['pattern_type_coverage']*100:.1f}%")
        print(f"  高信頼度パターン率: {accuracy['high_confidence_rate']*100:.1f}%")
        print(f"  総合精度: {accuracy['overall_accuracy']*100:.1f}%")
        
        print(f"\n📋 ルール生成精度:")
        print(f"  有効ルール率: {rules['rule_validity_rate']*100:.1f}%")
        print(f"  セキュリティルール数: {rules['security_rules_count']}")
        print(f"  品質ルール数: {rules['quality_rules_count']}")
        
        print(f"\n🎯 パフォーマンス目標達成状況:")
        for metric, result in performance['individual_results'].items():
            status = "✅ 達成" if result['passed'] else "❌ 未達成"
            print(f"  {metric}: {status} ({result['actual']:.2f} / {result['target']:.2f})")
        
        # プロジェクトプロファイル表示
        if report.get('project_profile'):
            profile = report['project_profile']
            print(f"\n🏗️ プロジェクトプロファイル:")
            print(f"  プロジェクトタイプ: {profile.project_type}")
            print(f"  主要フレームワーク: {', '.join(profile.primary_frameworks)}")
            print(f"  複雑度レベル: {profile.complexity_level}")
            print(f"  チーム規模推定: {profile.team_size_indicator}")
            
    else:
        print(f"❌ テスト失敗: {report.get('reason', '不明なエラー')}")
    
    # 詳細結果をJSONで保存
    report_path = Path("/mnt/c/Users/tky99/dev/qualitygate/test_results/integration_test_report.json")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        # データクラスをシリアライズ可能な形式に変換
        serializable_report = json.loads(json.dumps(report, default=str))
        json.dump(serializable_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 詳細レポート保存: {report_path}")
    
    return report['overall_status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
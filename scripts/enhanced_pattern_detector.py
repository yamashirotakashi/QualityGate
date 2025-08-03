#!/usr/bin/env python3
"""
QualityGate Phase 3A Week 2 - Enhanced Pattern Detector
高精度コードパターン自動検出エンジン

Week 2 強化内容:
1. より詳細なASTパターン解析
2. 統計的信頼度計算
3. プロジェクト固有パターン学習
4. False Positive削減アルゴリズム
"""

import ast
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from enum import Enum
import statistics

class PatternType(Enum):
    """パターンタイプ分類"""
    NAMING_CONVENTION = "naming_convention"
    IMPORT_STYLE = "import_style"
    CODE_STRUCTURE = "code_structure"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION = "documentation"
    COMPLEXITY = "complexity"
    SECURITY = "security"
    PROJECT_SPECIFIC = "project_specific"

@dataclass
class EnhancedCodePattern:
    """強化されたコードパターン"""
    pattern_id: str
    pattern_type: PatternType
    pattern_regex: str
    confidence_score: float  # 0.0-1.0
    frequency: int
    evidence_files: List[str]
    counter_examples: List[str]
    suggested_message: str
    severity: str  # CRITICAL, HIGH, INFO
    auto_fixable: bool = False
    related_patterns: List[str] = None
    
    def __post_init__(self):
        if self.related_patterns is None:
            self.related_patterns = []

@dataclass
class ProjectProfile:
    """プロジェクトプロファイル"""
    project_type: str  # web, cli, library, data_science, etc.
    primary_frameworks: List[str]
    coding_style: Dict[str, str]
    complexity_level: str  # simple, medium, complex
    team_size_indicator: str  # solo, small, medium, large
    maturity_level: str  # prototype, development, production

class EnhancedPatternDetector:
    """強化されたパターン検出エンジン"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.detected_patterns: List[EnhancedCodePattern] = []
        self.project_profile: Optional[ProjectProfile] = None
        
        # 検出精度向上のための閾値
        self.min_pattern_frequency = 3
        self.min_confidence_score = 0.7
        self.max_false_positive_rate = 0.15
        
        # プロジェクトタイプ判定ルール
        self.project_type_indicators = {
            'web': ['django', 'flask', 'fastapi', 'starlette', 'tornado'],
            'cli': ['click', 'argparse', 'typer', 'fire'],
            'data_science': ['pandas', 'numpy', 'sklearn', 'matplotlib', 'jupyter'],
            'library': ['setuptools', '__init__.py', 'setup.py'],
            'testing': ['pytest', 'unittest', 'nose', 'tox']
        }
        
        # 命名規則パターン（より詳細）
        self.naming_patterns = {
            'snake_case_functions': {
                'regex': r'^[a-z_][a-z0-9_]*$',
                'counter_regex': r'^[A-Z][a-zA-Z0-9]*$|^[a-z][a-zA-Z0-9]*$',
                'message': 'このプロジェクトではsnake_case関数名が標準です'
            },
            'camel_case_classes': {
                'regex': r'^[A-Z][a-zA-Z0-9]*$',
                'counter_regex': r'^[a-z_][a-z0-9_]*$',
                'message': 'このプロジェクトではCamelCaseクラス名が標準です'
            },
            'upper_case_constants': {
                'regex': r'^[A-Z][A-Z0-9_]*$',
                'counter_regex': r'^[a-z_][a-z0-9_]*$',
                'message': 'このプロジェクトでは定数はUPPER_CASEで命名します'
            },
            'private_methods': {
                'regex': r'^_[a-z_][a-z0-9_]*$',
                'counter_regex': r'^[a-z_][a-z0-9_]*$',
                'message': 'プライベートメソッドには先頭にアンダースコアを付けてください'
            }
        }
        
        # インポートスタイルパターン
        self.import_style_patterns = {
            'relative_imports': {
                'regex': r'from\s+\.+[a-zA-Z0-9_.]*\s+import',
                'message': 'このプロジェクトでは相対インポートが使用されています'
            },
            'absolute_imports': {
                'regex': r'from\s+[a-zA-Z][a-zA-Z0-9_.]*\s+import',
                'message': 'このプロジェクトでは絶対インポートが使用されています'
            },
            'grouped_imports': {
                'regex': r'import\s+[a-zA-Z0-9_.]+\nimport\s+[a-zA-Z0-9_.]+',
                'message': 'インポート文はグループ化されています'
            }
        }
        
        # エラーハンドリングパターン
        self.error_handling_patterns = {
            'specific_exceptions': {
                'regex': r'except\s+[A-Z][a-zA-Z]*Error',
                'message': '具体的な例外タイプが使用されています'
            },
            'bare_except': {
                'regex': r'except\s*:',
                'message': 'bare except文の使用が検出されました',
                'severity': 'HIGH'
            },
            'finally_blocks': {
                'regex': r'finally\s*:',
                'message': 'finallyブロックが適切に使用されています'
            }
        }
    
    def analyze_project_structure(self, file_results: List[Dict]) -> ProjectProfile:
        """プロジェクト構造分析してプロファイル作成"""
        # インポート分析でフレームワーク検出
        all_imports = []
        for result in file_results:
            if 'imports' in result:
                all_imports.extend(result['imports'])
        
        import_counter = Counter(all_imports)
        
        # プロジェクトタイプ判定
        project_type = 'general'
        detected_frameworks = []
        
        for ptype, indicators in self.project_type_indicators.items():
            for indicator in indicators:
                if any(indicator in imp for imp in all_imports):
                    project_type = ptype
                    detected_frameworks.append(indicator)
                    break
        
        # コーディングスタイル分析
        function_names = []
        class_names = []
        
        for result in file_results:
            if 'functions' in result:
                function_names.extend(result['functions'])
            if 'classes' in result:
                class_names.extend(result['classes'])
        
        # 命名規則分析
        coding_style = {}
        
        if function_names:
            snake_case_ratio = sum(1 for name in function_names 
                                 if re.match(r'^[a-z_][a-z0-9_]*$', name)) / len(function_names)
            coding_style['function_naming'] = 'snake_case' if snake_case_ratio > 0.7 else 'mixed'
        
        if class_names:
            camel_case_ratio = sum(1 for name in class_names 
                                 if re.match(r'^[A-Z][a-zA-Z0-9]*$', name)) / len(class_names)
            coding_style['class_naming'] = 'camel_case' if camel_case_ratio > 0.7 else 'mixed'
        
        # 複雑度レベル
        avg_complexity = statistics.mean([r.get('complexity_score', 0) for r in file_results]) if file_results else 0
        
        if avg_complexity < 5:
            complexity_level = 'simple'
        elif avg_complexity < 15:
            complexity_level = 'medium'
        else:
            complexity_level = 'complex'
        
        # チームサイズ推定（ファイル数とコメント密度から）
        total_files = len(file_results)
        if total_files < 10:
            team_size_indicator = 'solo'
        elif total_files < 50:
            team_size_indicator = 'small'
        else:
            team_size_indicator = 'medium'
        
        return ProjectProfile(
            project_type=project_type,
            primary_frameworks=detected_frameworks,
            coding_style=coding_style,
            complexity_level=complexity_level,
            team_size_indicator=team_size_indicator,
            maturity_level='development'  # 初期値
        )
    
    def detect_naming_patterns(self, file_results: List[Dict]) -> List[EnhancedCodePattern]:
        """命名規則パターン検出"""
        patterns = []
        
        # 関数名収集
        all_function_names = []
        function_files = {}
        
        for result in file_results:
            if 'functions' in result:
                for func_name in result['functions']:
                    all_function_names.append(func_name)
                    function_files[func_name] = result.get('file_path', 'unknown')
        
        # クラス名収集
        all_class_names = []
        class_files = {}
        
        for result in file_results:
            if 'classes' in result:
                for class_name in result['classes']:
                    all_class_names.append(class_name)
                    class_files[class_name] = result.get('file_path', 'unknown')
        
        # 関数命名パターン分析
        if len(all_function_names) >= self.min_pattern_frequency:
            snake_case_functions = [name for name in all_function_names 
                                  if re.match(r'^[a-z_][a-z0-9_]*$', name)]
            
            confidence = len(snake_case_functions) / len(all_function_names)
            
            if confidence >= self.min_confidence_score:
                patterns.append(EnhancedCodePattern(
                    pattern_id='snake_case_functions',
                    pattern_type=PatternType.NAMING_CONVENTION,
                    pattern_regex=r'def\s+[A-Z][a-zA-Z0-9]*\s*\(',
                    confidence_score=confidence,
                    frequency=len(snake_case_functions),
                    evidence_files=list(set(function_files[name] for name in snake_case_functions[:5])),
                    counter_examples=[name for name in all_function_names 
                                    if not re.match(r'^[a-z_][a-z0-9_]*$', name)][:3],
                    suggested_message=f'このプロジェクトではsnake_case関数名が標準です（適用率: {confidence:.1%}）',
                    severity='INFO',
                    auto_fixable=False
                ))
        
        # クラス命名パターン分析
        if len(all_class_names) >= self.min_pattern_frequency:
            camel_case_classes = [name for name in all_class_names 
                                if re.match(r'^[A-Z][a-zA-Z0-9]*$', name)]
            
            confidence = len(camel_case_classes) / len(all_class_names)
            
            if confidence >= self.min_confidence_score:
                patterns.append(EnhancedCodePattern(
                    pattern_id='camel_case_classes',
                    pattern_type=PatternType.NAMING_CONVENTION,
                    pattern_regex=r'class\s+[a-z][a-zA-Z0-9]*\s*[:\(]',
                    confidence_score=confidence,
                    frequency=len(camel_case_classes),
                    evidence_files=list(set(class_files[name] for name in camel_case_classes[:5])),
                    counter_examples=[name for name in all_class_names 
                                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name)][:3],
                    suggested_message=f'このプロジェクトではCamelCaseクラス名が標準です（適用率: {confidence:.1%}）',
                    severity='INFO',
                    auto_fixable=False
                ))
        
        return patterns
    
    def detect_import_patterns(self, file_results: List[Dict]) -> List[EnhancedCodePattern]:
        """インポートパターン検出"""
        patterns = []
        
        all_imports = []
        import_files = {}
        
        for result in file_results:
            if 'imports' in result:
                for imp in result['imports']:
                    all_imports.append(imp)
                    import_files[imp] = result.get('file_path', 'unknown')
        
        if not all_imports:
            return patterns
        
        # よく使用されるインポートパターン
        import_counter = Counter(all_imports)
        
        # 頻出インポートをプロジェクト固有パターンとして検出
        for import_name, frequency in import_counter.most_common(10):
            if frequency >= self.min_pattern_frequency:
                confidence = min(0.95, frequency / len(file_results))
                
                if confidence >= self.min_confidence_score:
                    patterns.append(EnhancedCodePattern(
                        pattern_id=f'common_import_{import_name.replace(".", "_")}',
                        pattern_type=PatternType.IMPORT_STYLE,
                        pattern_regex=f'import\\s+(?!{re.escape(import_name)})',
                        confidence_score=confidence,
                        frequency=frequency,
                        evidence_files=[import_files[import_name]],
                        counter_examples=[],
                        suggested_message=f'このプロジェクトでは{import_name}が標準的に使用されています',
                        severity='INFO',
                        auto_fixable=False
                    ))
        
        # 相対インポート vs 絶対インポート
        relative_imports = [imp for imp in all_imports if imp.startswith('.')]
        if len(relative_imports) >= self.min_pattern_frequency:
            confidence = len(relative_imports) / len(all_imports)
            
            if confidence >= 0.3:  # 相対インポートは30%でも重要
                patterns.append(EnhancedCodePattern(
                    pattern_id='relative_imports',
                    pattern_type=PatternType.IMPORT_STYLE,
                    pattern_regex=r'from\s+[a-zA-Z][a-zA-Z0-9_.]*\s+import',
                    confidence_score=confidence,
                    frequency=len(relative_imports),
                    evidence_files=list(set(import_files.get(imp, 'unknown') for imp in relative_imports[:3])),
                    counter_examples=[],
                    suggested_message=f'このプロジェクトでは相対インポートが使用されています（使用率: {confidence:.1%}）',
                    severity='INFO',
                    auto_fixable=False
                ))
        
        return patterns
    
    def detect_code_structure_patterns(self, file_results: List[Dict]) -> List[EnhancedCodePattern]:
        """コード構造パターン検出（強化版）"""
        patterns = []
        
        # エラーハンドリングパターン
        files_with_try_except = 0
        files_with_specific_exceptions = 0
        files_with_bare_except = 0
        files_with_docstrings = 0
        files_with_type_hints = 0
        files_with_logging = 0
        files_with_classes = 0
        files_with_inheritance = 0
        
        structure_files = {
            'try_except': [],
            'specific_exceptions': [],
            'bare_except': [],
            'docstrings': [],
            'type_hints': [],
            'logging': [],
            'inheritance': []
        }
        
        for result in file_results:
            file_path = result.get('file_path', '')
            
            # ファイル内容が必要な場合は実際に読み込み
            try:
                full_path = self.project_path / file_path
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # エラーハンドリング分析
                    if 'try:' in content:
                        files_with_try_except += 1
                        structure_files['try_except'].append(file_path)
                        
                        if re.search(r'except\s+[A-Z][a-zA-Z]*Error', content):
                            files_with_specific_exceptions += 1
                            structure_files['specific_exceptions'].append(file_path)
                        
                        if re.search(r'except\s*:', content):
                            files_with_bare_except += 1
                            structure_files['bare_except'].append(file_path)
                    
                    # ドキュメンテーションパターン
                    if '"""' in content or "'''" in content:
                        files_with_docstrings += 1
                        structure_files['docstrings'].append(file_path)
                    
                    # 型ヒント分析
                    if re.search(r'->\s*[A-Za-z]', content) or re.search(r':\s*[A-Z][a-zA-Z]*', content):
                        files_with_type_hints += 1
                        structure_files['type_hints'].append(file_path)
                    
                    # ログ記録分析
                    if re.search(r'(logging|log\.|logger)', content):
                        files_with_logging += 1
                        structure_files['logging'].append(file_path)
                    
                    # クラス継承分析
                    if 'classes' in result and result['classes']:
                        files_with_classes += 1
                        if re.search(r'class\s+\w+\([^)]+\):', content):
                            files_with_inheritance += 1
                            structure_files['inheritance'].append(file_path)
                            
            except Exception:
                continue
        
        total_files = len(file_results)
        
        # 具体的例外処理パターン
        if files_with_specific_exceptions >= self.min_pattern_frequency:
            confidence = files_with_specific_exceptions / max(files_with_try_except, 1)
            
            if confidence >= self.min_confidence_score:
                patterns.append(EnhancedCodePattern(
                    pattern_id='specific_exception_handling',
                    pattern_type=PatternType.ERROR_HANDLING,
                    pattern_regex=r'except\s*:',
                    confidence_score=confidence,
                    frequency=files_with_specific_exceptions,
                    evidence_files=structure_files['specific_exceptions'][:3],
                    counter_examples=[],
                    suggested_message=f'このプロジェクトでは具体的な例外タイプを指定した処理が標準です',
                    severity='HIGH',
                    auto_fixable=False
                ))
        
        # ドキュメンテーションパターン
        if files_with_docstrings >= self.min_pattern_frequency:
            confidence = files_with_docstrings / total_files
            if confidence >= 0.5:  # 50%以上でパターンとして認識
                patterns.append(EnhancedCodePattern(
                    pattern_id='docstring_usage',
                    pattern_type=PatternType.DOCUMENTATION,
                    pattern_regex=r'def\s+\w+[^:]*:\s*$',
                    confidence_score=confidence,
                    frequency=files_with_docstrings,
                    evidence_files=structure_files['docstrings'][:3],
                    counter_examples=[],
                    suggested_message=f'このプロジェクトではdocstringによる文書化が標準です（適用率: {confidence:.1%}）',
                    severity='INFO',
                    auto_fixable=False
                ))
        
        # 型ヒントパターン
        if files_with_type_hints >= self.min_pattern_frequency:
            confidence = files_with_type_hints / total_files
            if confidence >= 0.4:  # 40%以上でパターンとして認識
                patterns.append(EnhancedCodePattern(
                    pattern_id='type_hints_usage',
                    pattern_type=PatternType.CODE_STRUCTURE,
                    pattern_regex=r'def\s+\w+\([^)]*\)\s*$',
                    confidence_score=confidence,
                    frequency=files_with_type_hints,
                    evidence_files=structure_files['type_hints'][:3],
                    counter_examples=[],
                    suggested_message=f'このプロジェクトでは型ヒントの使用が推奨されています（適用率: {confidence:.1%}）',
                    severity='INFO',
                    auto_fixable=False
                ))
        
        # ログ記録パターン
        if files_with_logging >= self.min_pattern_frequency:
            confidence = files_with_logging / total_files
            if confidence >= 0.3:  # 30%以上でパターンとして認識
                patterns.append(EnhancedCodePattern(
                    pattern_id='logging_usage',
                    pattern_type=PatternType.CODE_STRUCTURE,
                    pattern_regex=r'print\s*\(',
                    confidence_score=confidence,
                    frequency=files_with_logging,
                    evidence_files=structure_files['logging'][:3],
                    counter_examples=[],
                    suggested_message=f'このプロジェクトではloggingモジュールの使用が標準です',
                    severity='INFO',
                    auto_fixable=False
                ))
        
        # クラス継承パターン
        if files_with_inheritance >= 2:  # 最低2ファイル
            confidence = files_with_inheritance / max(files_with_classes, 1)
            if confidence >= 0.4:  # 40%以上のクラスが継承を使用
                patterns.append(EnhancedCodePattern(
                    pattern_id='class_inheritance_pattern',
                    pattern_type=PatternType.CODE_STRUCTURE,
                    pattern_regex=r'class\s+\w+\s*:',
                    confidence_score=confidence,
                    frequency=files_with_inheritance,
                    evidence_files=structure_files['inheritance'][:3],
                    counter_examples=[],
                    suggested_message=f'このプロジェクトではクラス継承を活用した設計が標準です',
                    severity='INFO',
                    auto_fixable=False
                ))
        
        # bare except警告
        if files_with_bare_except > 0:
            patterns.append(EnhancedCodePattern(
                pattern_id='bare_except_warning',
                pattern_type=PatternType.ERROR_HANDLING,
                pattern_regex=r'except\s*:',
                confidence_score=1.0,
                frequency=files_with_bare_except,
                evidence_files=structure_files['bare_except'][:3],
                counter_examples=[],
                suggested_message='bare except文は避けて、具体的な例外タイプを指定してください',
                severity='HIGH',
                auto_fixable=False
            ))
        
        return patterns
    
    def calculate_pattern_quality_score(self, pattern: EnhancedCodePattern) -> float:
        """パターン品質スコア計算"""
        # 基本信頼度
        base_score = pattern.confidence_score
        
        # 頻度による重み付け
        frequency_weight = min(1.0, pattern.frequency / 10.0)
        
        # パターンタイプによる重み付け
        type_weights = {
            PatternType.SECURITY: 1.0,
            PatternType.ERROR_HANDLING: 0.9,
            PatternType.NAMING_CONVENTION: 0.8,
            PatternType.CODE_STRUCTURE: 0.7,
            PatternType.IMPORT_STYLE: 0.6,
            PatternType.PROJECT_SPECIFIC: 0.5
        }
        
        type_weight = type_weights.get(pattern.pattern_type, 0.5)
        
        # 最終スコア計算
        quality_score = base_score * 0.6 + frequency_weight * 0.2 + type_weight * 0.2
        
        return min(1.0, quality_score)
    
    def enhance_pattern_detection(self, file_results: List[Dict]) -> List[EnhancedCodePattern]:
        """強化されたパターン検出実行"""
        print("🔍 強化パターン検出開始...")
        
        # プロジェクトプロファイル作成
        self.project_profile = self.analyze_project_structure(file_results)
        
        all_patterns = []
        
        # 各種パターン検出
        all_patterns.extend(self.detect_naming_patterns(file_results))
        all_patterns.extend(self.detect_import_patterns(file_results))
        all_patterns.extend(self.detect_code_structure_patterns(file_results))
        
        # パターン品質フィルタリング
        high_quality_patterns = []
        for pattern in all_patterns:
            quality_score = self.calculate_pattern_quality_score(pattern)
            
            if quality_score >= 0.75:  # 高品質パターンのみ
                pattern.confidence_score = quality_score  # 品質スコアで更新
                high_quality_patterns.append(pattern)
        
        # パターン関連性分析
        self.analyze_pattern_relationships(high_quality_patterns)
        
        self.detected_patterns = high_quality_patterns
        
        print(f"✅ パターン検出完了: {len(high_quality_patterns)}個の高品質パターンを検出")
        
        return high_quality_patterns
    
    def analyze_pattern_relationships(self, patterns: List[EnhancedCodePattern]):
        """パターン間の関連性分析"""
        for i, pattern1 in enumerate(patterns):
            for j, pattern2 in enumerate(patterns[i+1:], i+1):
                # 同じタイプのパターンは関連性が高い
                if pattern1.pattern_type == pattern2.pattern_type:
                    pattern1.related_patterns.append(pattern2.pattern_id)
                    pattern2.related_patterns.append(pattern1.pattern_id)
    
    def generate_project_specific_rules(self) -> List[Dict[str, str]]:
        """プロジェクト固有ルール生成"""
        rules = []
        
        for pattern in self.detected_patterns:
            if pattern.confidence_score >= 0.8:  # 高信頼度パターンのみ
                rule = {
                    'pattern_id': pattern.pattern_id,
                    'severity': pattern.severity,
                    'pattern': pattern.pattern_regex,
                    'message': pattern.suggested_message,
                    'category': pattern.pattern_type.value,
                    'confidence': pattern.confidence_score,
                    'auto_generated': True,
                    'evidence_count': pattern.frequency
                }
                rules.append(rule)
        
        return rules
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """検出統計情報取得"""
        if not self.detected_patterns:
            return {}
        
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        total_confidence = 0
        
        for pattern in self.detected_patterns:
            by_type[pattern.pattern_type.value] += 1
            by_severity[pattern.severity] += 1
            total_confidence += pattern.confidence_score
        
        return {
            'total_patterns': len(self.detected_patterns),
            'average_confidence': total_confidence / len(self.detected_patterns),
            'patterns_by_type': dict(by_type),
            'patterns_by_severity': dict(by_severity),
            'project_profile': asdict(self.project_profile) if self.project_profile else None
        }

def main():
    """テスト用メインエントリーポイント"""
    project_path = "/mnt/c/Users/tky99/dev/qualitygate"
    
    print("🚀 Enhanced Pattern Detector テスト開始")
    print("=" * 60)
    
    # 簡易ファイル結果作成（実際のAST分析器と連携予定）
    test_file_results = [
        {
            'file_path': 'scripts/test_file.py',
            'functions': ['calculate_total', 'process_data', 'get_user_info'],
            'classes': ['DataProcessor', 'UserManager'],
            'imports': ['json', 'pathlib.Path', 'typing.Dict'],
            'complexity_score': 8
        },
        {
            'file_path': 'scripts/another_file.py',
            'functions': ['validate_input', 'save_results'],
            'classes': ['ResultHandler'],
            'imports': ['json', 'datetime', 'typing.List'],
            'complexity_score': 5
        }
    ]
    
    detector = EnhancedPatternDetector(project_path)
    
    # パターン検出実行
    patterns = detector.enhance_pattern_detection(test_file_results)
    
    # 結果表示
    print(f"\n🎯 検出結果:")
    for pattern in patterns:
        print(f"  • {pattern.pattern_id}: {pattern.suggested_message}")
        print(f"    信頼度: {pattern.confidence_score:.2f}, 頻度: {pattern.frequency}")
    
    # 統計情報
    stats = detector.get_detection_statistics()
    print(f"\n📊 統計情報:")
    print(f"  総パターン数: {stats.get('total_patterns', 0)}")
    print(f"  平均信頼度: {stats.get('average_confidence', 0):.2f}")
    
    # プロジェクト固有ルール生成
    rules = detector.generate_project_specific_rules()
    print(f"\n📋 生成ルール数: {len(rules)}")

if __name__ == "__main__":
    main()
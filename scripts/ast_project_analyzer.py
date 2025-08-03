#!/usr/bin/env python3
"""
QualityGate Phase 3A - 独立AST Project Analyzer
Python プロジェクト構造分析とパターン自動生成エンジン

設計原則:
1. 完全分離: リアルタイム処理への影響ゼロ
2. 非同期実行: バックグラウンド処理
3. 軽量設計: メモリ使用量 < 50MB
4. 結果キャッシュ: プロジェクト変更時のみ再分析
"""

import ast
import os
import sys
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class ProjectMetrics:
    """プロジェクト基本メトリクス"""
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    average_complexity: float = 0.0
    complexity_distribution: Dict[str, int] = None
    import_patterns: Dict[str, int] = None
    naming_patterns: Dict[str, int] = None
    
    def __post_init__(self):
        if self.complexity_distribution is None:
            self.complexity_distribution = {}
        if self.import_patterns is None:
            self.import_patterns = {}
        if self.naming_patterns is None:
            self.naming_patterns = {}

@dataclass
class CodePattern:
    """検出されたコードパターン"""
    pattern_type: str  # 'naming', 'import', 'structure', 'complexity'
    pattern: str
    confidence: float
    frequency: int
    examples: List[str]
    suggested_rule: Optional[str] = None

@dataclass
class ProjectAnalysisResult:
    """プロジェクト分析結果"""
    project_path: str
    analysis_timestamp: float
    metrics: ProjectMetrics
    detected_patterns: List[CodePattern]
    suggested_quality_rules: List[Dict[str, str]]
    file_analysis_results: Dict[str, Dict] = None
    
    def __post_init__(self):
        if self.file_analysis_results is None:
            self.file_analysis_results = {}

class ASTProjectAnalyzer:
    """独立AST Project Analyzer - バックグラウンド実行専用"""
    
    def __init__(self, project_path: str, cache_dir: Optional[str] = None):
        self.project_path = Path(project_path)
        self.cache_dir = Path(cache_dir or self.project_path / ".qualitygate_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # 分析状態管理
        self.is_analyzing = False
        self.analysis_progress = 0.0
        self.last_analysis_time = 0
        self.analysis_result: Optional[ProjectAnalysisResult] = None
        
        # パフォーマンス制限
        self.max_file_size = 100 * 1024  # 100KB
        self.max_files_per_analysis = 1000
        self.analysis_timeout = 30  # 30秒
        
        # パターン検出設定
        self.naming_patterns = {
            'snake_case_function': r'^[a-z_][a-z0-9_]*$',
            'camel_case_class': r'^[A-Z][a-zA-Z0-9]*$',
            'upper_case_constant': r'^[A-Z][A-Z0-9_]*$',
            'private_method': r'^_[a-z_][a-z0-9_]*$'
        }
    
    def get_project_hash(self) -> str:
        """プロジェクト状態のハッシュ値計算（キャッシュキー用）"""
        try:
            # Pythonファイルの更新時刻を集計
            python_files = list(self.project_path.rglob("*.py"))
            if not python_files:
                return "empty_project"
            
            # ファイル数とサイズの簡易ハッシュ
            total_size = sum(f.stat().st_size for f in python_files if f.exists())
            total_files = len(python_files)
            latest_mtime = max(f.stat().st_mtime for f in python_files if f.exists())
            
            hash_input = f"{total_files}:{total_size}:{latest_mtime}"
            return hashlib.md5(hash_input.encode()).hexdigest()[:16]
            
        except Exception:
            return f"error_{int(time.time())}"
    
    def load_cached_analysis(self) -> Optional[ProjectAnalysisResult]:
        """キャッシュされた分析結果を読み込み"""
        try:
            project_hash = self.get_project_hash()
            cache_file = self.cache_dir / f"analysis_{project_hash}.json"
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # データクラスに復元
                metrics = ProjectMetrics(**data['metrics'])
                patterns = [CodePattern(**p) for p in data['detected_patterns']]
                
                result = ProjectAnalysisResult(
                    project_path=data['project_path'],
                    analysis_timestamp=data['analysis_timestamp'],
                    metrics=metrics,
                    detected_patterns=patterns,
                    suggested_quality_rules=data['suggested_quality_rules'],
                    file_analysis_results=data.get('file_analysis_results', {})
                )
                
                # キャッシュが新しい場合のみ使用（24時間以内）
                if time.time() - result.analysis_timestamp < 86400:
                    return result
                    
        except Exception as e:
            print(f"キャッシュ読み込みエラー: {e}")
        
        return None
    
    def save_analysis_cache(self, result: ProjectAnalysisResult):
        """分析結果をキャッシュに保存"""
        try:
            project_hash = self.get_project_hash()
            cache_file = self.cache_dir / f"analysis_{project_hash}.json"
            
            # データクラスを辞書に変換
            data = {
                'project_path': result.project_path,
                'analysis_timestamp': result.analysis_timestamp,
                'metrics': asdict(result.metrics),
                'detected_patterns': [asdict(p) for p in result.detected_patterns],
                'suggested_quality_rules': result.suggested_quality_rules,
                'file_analysis_results': result.file_analysis_results
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")
    
    def analyze_python_file(self, file_path: Path) -> Optional[Dict]:
        """単一Pythonファイルの分析"""
        try:
            # ファイルサイズチェック
            if file_path.stat().st_size > self.max_file_size:
                return None
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # AST解析
            tree = ast.parse(content, filename=str(file_path))
            
            # 基本メトリクス収集
            analyzer = FileASTAnalyzer()
            analyzer.visit(tree)
            
            return {
                'file_path': str(file_path.relative_to(self.project_path)),
                'lines_of_code': len(content.splitlines()),
                'functions': analyzer.functions,
                'classes': analyzer.classes,
                'imports': analyzer.imports,
                'complexity_score': analyzer.complexity_score,
                'naming_issues': analyzer.naming_issues
            }
            
        except Exception as e:
            return {
                'file_path': str(file_path.relative_to(self.project_path)),
                'error': str(e),
                'analysis_failed': True
            }
    
    def detect_code_patterns(self, file_results: List[Dict]) -> List[CodePattern]:
        """コードパターン検出（強化版パターン検出器を使用）"""
        try:
            # 強化パターン検出器をインポート
            from enhanced_pattern_detector import EnhancedPatternDetector
            
            # 強化検出器を使用
            enhanced_detector = EnhancedPatternDetector(str(self.project_path))
            enhanced_patterns = enhanced_detector.enhance_pattern_detection(file_results)
            
            # EnhancedCodePatternをCodePatternに変換
            patterns = []
            for ep in enhanced_patterns:
                patterns.append(CodePattern(
                    pattern_type=ep.pattern_type.value,
                    pattern=ep.pattern_id,
                    confidence=ep.confidence_score,
                    frequency=ep.frequency,
                    examples=ep.evidence_files[:3],
                    suggested_rule=ep.suggested_message
                ))
            
            return patterns
            
        except ImportError:
            # フォールバック: 基本パターン検出
            return self._detect_basic_patterns(file_results)
    
    def _detect_basic_patterns(self, file_results: List[Dict]) -> List[CodePattern]:
        """基本パターン検出（フォールバック用）"""
        patterns = []
        
        # インポートパターン分析
        import_counter = Counter()
        for result in file_results:
            if 'imports' in result:
                for imp in result['imports']:
                    import_counter[imp] += 1
        
        # 頻出インポートをパターンとして記録
        for import_name, frequency in import_counter.most_common(10):
            if frequency >= 3:  # 3回以上出現するインポート
                patterns.append(CodePattern(
                    pattern_type='import',
                    pattern=import_name,
                    confidence=min(0.9, frequency / len(file_results)),
                    frequency=frequency,
                    examples=[f"import {import_name}"],
                    suggested_rule=f"推奨インポート: {import_name}"
                ))
        
        # 命名パターン分析
        function_names = []
        class_names = []
        
        for result in file_results:
            if 'functions' in result:
                function_names.extend(result['functions'])
            if 'classes' in result:
                class_names.extend(result['classes'])
        
        # 関数命名パターン検出
        if function_names:
            snake_case_count = sum(1 for name in function_names if name.islower() and '_' in name)
            if snake_case_count / len(function_names) > 0.7:
                patterns.append(CodePattern(
                    pattern_type='naming',
                    pattern='snake_case_functions',
                    confidence=snake_case_count / len(function_names),
                    frequency=snake_case_count,
                    examples=function_names[:3],
                    suggested_rule="関数名はsnake_case形式を使用"
                ))
        
        # クラス命名パターン検出
        if class_names:
            camel_case_count = sum(1 for name in class_names if name[0].isupper())
            if camel_case_count / len(class_names) > 0.7:
                patterns.append(CodePattern(
                    pattern_type='naming',
                    pattern='camel_case_classes',
                    confidence=camel_case_count / len(class_names),
                    frequency=camel_case_count,
                    examples=class_names[:3],
                    suggested_rule="クラス名はCamelCase形式を使用"
                ))
        
        return patterns
    
    def generate_quality_rules(self, patterns: List[CodePattern]) -> List[Dict[str, str]]:
        """品質ルール自動生成（強化版）"""
        try:
            # 強化パターン検出器からルール生成機能を使用
            from enhanced_pattern_detector import EnhancedPatternDetector
            
            enhanced_detector = EnhancedPatternDetector(str(self.project_path))
            enhanced_detector.detected_patterns = []
            
            # CodePatternをEnhancedCodePatternに変換
            for pattern in patterns:
                if pattern.confidence > 0.7:
                    from enhanced_pattern_detector import EnhancedCodePattern, PatternType
                    
                    # パターンタイプをEnumに変換
                    try:
                        pattern_type_enum = PatternType(pattern.pattern_type)
                    except ValueError:
                        pattern_type_enum = PatternType.PROJECT_SPECIFIC
                    
                    enhanced_pattern = EnhancedCodePattern(
                        pattern_id=pattern.pattern,
                        pattern_type=pattern_type_enum,
                        pattern_regex=self._generate_regex_for_pattern(pattern),
                        confidence_score=pattern.confidence,
                        frequency=pattern.frequency,
                        evidence_files=pattern.examples,
                        counter_examples=[],
                        suggested_message=pattern.suggested_rule,
                        severity='INFO'
                    )
                    enhanced_detector.detected_patterns.append(enhanced_pattern)
            
            # 強化されたルール生成
            return enhanced_detector.generate_project_specific_rules()
            
        except ImportError:
            # フォールバック: 基本ルール生成
            return self._generate_basic_rules(patterns)
    
    def _generate_regex_for_pattern(self, pattern: CodePattern) -> str:
        """パターンから正規表現を生成"""
        if pattern.pattern_type == 'naming':
            if 'snake_case' in pattern.pattern:
                return r'def\s+[A-Z][a-zA-Z0-9]*\s*\('
            elif 'camel_case' in pattern.pattern:
                return r'class\s+[a-z][a-zA-Z0-9]*\s*[:\(]'
        elif pattern.pattern_type == 'import':
            import re
            return f'import\\s+(?!{re.escape(pattern.pattern)})'
        
        return r'.*'  # デフォルト
    
    def _generate_basic_rules(self, patterns: List[CodePattern]) -> List[Dict[str, str]]:
        """基本ルール生成（フォールバック用）"""
        rules = []
        
        for pattern in patterns:
            if pattern.confidence > 0.7:  # 高信頼度パターンのみ
                if pattern.pattern_type == 'import':
                    rules.append({
                        'severity': 'INFO',
                        'pattern': f'import\\s+(?!{pattern.pattern})',
                        'message': f'推奨インポート {pattern.pattern} の使用を検討してください',
                        'category': 'project_specific'
                    })
                elif pattern.pattern_type == 'naming':
                    if 'snake_case' in pattern.pattern:
                        rules.append({
                            'severity': 'INFO',
                            'pattern': r'def\s+[A-Z][a-zA-Z0-9]*\s*\(',
                            'message': 'このプロジェクトではsnake_case関数名が推奨されています',
                            'category': 'naming_convention'
                        })
                    elif 'camel_case' in pattern.pattern:
                        rules.append({
                            'severity': 'INFO',
                            'pattern': r'class\s+[a-z][a-zA-Z0-9]*\s*[:\(]',
                            'message': 'このプロジェクトではCamelCaseクラス名が推奨されています',
                            'category': 'naming_convention'
                        })
        
        return rules
    
    def analyze_project_async(self) -> None:
        """非同期プロジェクト分析（バックグラウンド実行）"""
        if self.is_analyzing:
            return
        
        def analysis_worker():
            try:
                self.is_analyzing = True
                self.analysis_progress = 0.0
                start_time = time.time()
                
                # キャッシュチェック
                cached_result = self.load_cached_analysis()
                if cached_result:
                    self.analysis_result = cached_result
                    self.analysis_progress = 1.0
                    self.is_analyzing = False
                    return
                
                # Pythonファイル収集
                python_files = list(self.project_path.rglob("*.py"))
                python_files = [f for f in python_files 
                              if f.is_file() and not any(part.startswith('.') for part in f.parts)]
                
                if len(python_files) > self.max_files_per_analysis:
                    python_files = python_files[:self.max_files_per_analysis]
                
                if not python_files:
                    self.is_analyzing = False
                    return
                
                # 並列ファイル分析
                file_results = []
                with ThreadPoolExecutor(max_workers=4) as executor:
                    future_to_file = {
                        executor.submit(self.analyze_python_file, file_path): file_path 
                        for file_path in python_files
                    }
                    
                    for i, future in enumerate(as_completed(future_to_file, timeout=self.analysis_timeout)):
                        result = future.result()
                        if result:
                            file_results.append(result)
                        
                        # 進捗更新
                        self.analysis_progress = (i + 1) / len(python_files) * 0.8
                        
                        # タイムアウトチェック
                        if time.time() - start_time > self.analysis_timeout:
                            break
                
                # パターン検出
                detected_patterns = self.detect_code_patterns(file_results)
                self.analysis_progress = 0.9
                
                # 品質ルール生成
                quality_rules = self.generate_quality_rules(detected_patterns)
                
                # メトリクス計算
                total_lines = sum(r.get('lines_of_code', 0) for r in file_results)
                total_functions = sum(len(r.get('functions', [])) for r in file_results)
                total_classes = sum(len(r.get('classes', [])) for r in file_results)
                
                metrics = ProjectMetrics(
                    total_files=len(file_results),
                    total_lines=total_lines,
                    total_functions=total_functions,
                    total_classes=total_classes,
                    average_complexity=sum(r.get('complexity_score', 0) for r in file_results) / len(file_results) if file_results else 0
                )
                
                # 結果作成
                self.analysis_result = ProjectAnalysisResult(
                    project_path=str(self.project_path),
                    analysis_timestamp=time.time(),
                    metrics=metrics,
                    detected_patterns=detected_patterns,
                    suggested_quality_rules=quality_rules,
                    file_analysis_results={r['file_path']: r for r in file_results}
                )
                
                # キャッシュ保存
                self.save_analysis_cache(self.analysis_result)
                
                self.analysis_progress = 1.0
                self.last_analysis_time = time.time()
                
            except Exception as e:
                print(f"プロジェクト分析エラー: {e}")
            finally:
                self.is_analyzing = False
        
        # バックグラウンドスレッドで実行
        thread = threading.Thread(target=analysis_worker, daemon=True)
        thread.start()
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """分析状態取得"""
        return {
            'is_analyzing': self.is_analyzing,
            'progress': self.analysis_progress,
            'last_analysis_time': self.last_analysis_time,
            'has_result': self.analysis_result is not None,
            'cache_dir': str(self.cache_dir)
        }
    
    def get_analysis_result(self) -> Optional[ProjectAnalysisResult]:
        """分析結果取得"""
        return self.analysis_result
    
    def force_reanalysis(self):
        """強制再分析（キャッシュクリア）"""
        # キャッシュファイル削除
        for cache_file in self.cache_dir.glob("analysis_*.json"):
            cache_file.unlink()
        
        self.analysis_result = None
        self.analyze_project_async()

class FileASTAnalyzer(ast.NodeVisitor):
    """単一ファイルのAST分析"""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []
        self.complexity_score = 0
        self.naming_issues = []
    
    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        # 簡易複雑度計算
        self.complexity_score += 1 + len([n for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While, ast.Try))])
        
        # 命名チェック
        if not node.name.islower():
            self.naming_issues.append(f"Function {node.name} is not snake_case")
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        
        # 命名チェック
        if not node.name[0].isupper():
            self.naming_issues.append(f"Class {node.name} is not CamelCase")
        
        self.generic_visit(node)
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)

def main():
    """テスト用メインエントリーポイント"""
    project_path = "/mnt/c/Users/tky99/dev/qualitygate"
    
    print("🔍 AST Project Analyzer テスト開始")
    print("=" * 60)
    
    analyzer = ASTProjectAnalyzer(project_path)
    
    # 分析開始
    print("📊 プロジェクト分析開始...")
    analyzer.analyze_project_async()
    
    # 進捗監視
    while analyzer.is_analyzing:
        status = analyzer.get_analysis_status()
        print(f"進捗: {status['progress']*100:.1f}%")
        time.sleep(1)
    
    # 結果表示
    result = analyzer.get_analysis_result()
    if result:
        print("\n✅ 分析完了!")
        print(f"📁 ファイル数: {result.metrics.total_files}")
        print(f"📝 総行数: {result.metrics.total_lines}")
        print(f"🔧 関数数: {result.metrics.total_functions}")
        print(f"📦 クラス数: {result.metrics.total_classes}")
        print(f"🧮 平均複雑度: {result.metrics.average_complexity:.2f}")
        
        print(f"\n🎯 検出パターン数: {len(result.detected_patterns)}")
        for pattern in result.detected_patterns[:3]:
            print(f"  • {pattern.pattern_type}: {pattern.pattern} (信頼度: {pattern.confidence:.2f})")
        
        print(f"\n📋 生成ルール数: {len(result.suggested_quality_rules)}")
        for rule in result.suggested_quality_rules[:3]:
            print(f"  • {rule['severity']}: {rule['message']}")
    else:
        print("❌ 分析失敗")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
QualityGate Phase 2 - パフォーマンス最適化エンジン
高速パターンマッチングと最適化アルゴリズム
"""

import re
import time
import hashlib
import json
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path

class PerformanceOptimizer:
    """QualityGate用パフォーマンス最適化エンジン"""
    
    def __init__(self):
        self.compiled_patterns: Dict[str, re.Pattern] = {}
        self.pattern_cache: Dict[str, Tuple[str, str, Dict]] = {}
        self.skip_cache: Set[str] = set()
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'pattern_matches': 0,
            'skip_cache_hits': 0
        }
        
    def get_content_hash(self, content: str) -> str:
        """コンテンツのハッシュを生成（キャッシュキー用）"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    
    def is_likely_safe_content(self, content: str) -> bool:
        """明らかに安全なコンテンツの高速判定"""
        # 空または短すぎるコンテンツ
        if not content or len(content.strip()) < 3:
            return True
            
        # 危険キーワードが含まれている場合は安全とみなさない
        danger_keywords = ['sk_', 'pk_', 'api', 'key', 'secret', 'token', 'AKIA', 'rm', 'sudo', 'eval', 'exec', 'とりあえず', 'TODO', 'FIXME', 'console.log', 'print']
        content_lower = content.lower()
        for keyword in danger_keywords:
            if keyword.lower() in content_lower:
                return False
            
        # ASCII文字のみで明らかに安全なパターン
        if content.isascii() and len(content) < 50:
            safe_patterns = [
                re.compile(r'^[a-zA-Z0-9\s\-_\.]*$'),  # 基本文字のみ
                re.compile(r'^(ls|cd|pwd|echo|cat)\s'),  # 安全なコマンド
                re.compile(r'^\w+\s*=\s*\w+$'),  # 単純な変数代入
            ]
            for pattern in safe_patterns:
                if pattern.match(content.strip()):
                    return True
        
        return False
    
    def compile_patterns_optimized(self, patterns: Dict[str, str]) -> Dict[str, re.Pattern]:
        """パターンの最適化コンパイル"""
        compiled = {}
        
        # パターンを長さでソート（長いパターンを優先）
        sorted_patterns = sorted(patterns.items(), key=lambda x: len(x[0]), reverse=True)
        
        for pattern_str, message in sorted_patterns:
            try:
                # 複雑なパターンは事前コンパイルでキャッシュ
                if len(pattern_str) > 20 or any(char in pattern_str for char in r'.*+?{}[]()^$|\\'):
                    compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                    compiled[pattern_str] = compiled_pattern
                else:
                    # 単純なパターンは文字列検索で高速化
                    compiled[pattern_str] = pattern_str.lower()
                    
            except re.error:
                # 無効な正規表現はスキップ
                continue
                
        return compiled
    
    def fast_pattern_match(self, content: str, patterns: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """高速パターンマッチング"""
        content_lower = content.lower()
        
        # 直接正規表現でマッチング（キャッシュ機能付き）
        for pattern_str, message in patterns.items():
            try:
                # キャッシュから取得または新しくコンパイル
                if pattern_str not in self.compiled_patterns:
                    self.compiled_patterns[pattern_str] = re.compile(pattern_str, re.IGNORECASE)
                
                compiled_pattern = self.compiled_patterns[pattern_str]
                
                # パターンマッチング実行
                if compiled_pattern.search(content):
                    return pattern_str, message
                    
            except re.error:
                # 無効な正規表現はスキップ
                continue
        
        return None, None
    
    def analyze_with_cache(self, content: str, patterns: Dict[str, str], severity: str) -> Tuple[Optional[str], Optional[str]]:
        """キャッシュ機能付き分析"""
        # コンテンツハッシュを生成
        content_hash = self.get_content_hash(content)
        
        # スキップキャッシュチェック（安全と判定されたコンテンツのみ）
        if content_hash in self.skip_cache:
            self.stats['skip_cache_hits'] += 1
            return None, None
        
        # パターンキャッシュチェック
        cache_key = f"{content_hash}:{severity}"
        if cache_key in self.pattern_cache:
            self.stats['cache_hits'] += 1
            result = self.pattern_cache[cache_key]
            return result[0], result[1]
        
        self.stats['cache_misses'] += 1
        
        # 明らかに安全なコンテンツの高速判定
        if self.is_likely_safe_content(content):
            self.skip_cache.add(content_hash)
            return None, None
        
        # 実際のパターンマッチング
        pattern, message = self.fast_pattern_match(content, patterns)
        
        # 結果をキャッシュ
        if pattern:
            self.stats['pattern_matches'] += 1
            action = self._get_action_for_severity(severity)
            self.pattern_cache[cache_key] = (pattern, message, action)
            return pattern, message
        else:
            # マッチしない場合は重要度別にキャッシュ（スキップキャッシュは安全判定のみ）
            self.pattern_cache[cache_key] = (None, None, {})
            return None, None
    
    def _get_action_for_severity(self, severity: str) -> Dict:
        """重要度に応じたアクション情報を取得"""
        actions = {
            'CRITICAL': {'emoji': '🚫', 'prefix': '重大'},
            'HIGH': {'emoji': '⚠️', 'prefix': '警告'},
            'INFO': {'emoji': 'ℹ️', 'prefix': '情報'}
        }
        return actions.get(severity, {'emoji': '❓', 'prefix': '不明'})
    
    def optimize_for_size(self, content: str, max_length: int = 1000) -> str:
        """大きなコンテンツの最適化"""
        if len(content) <= max_length:
            return content
        
        # 重要な部分を抽出（先頭、末尾、キーワード周辺）
        important_keywords = [
            'password', 'api', 'key', 'token', 'secret',
            'rm -rf', 'sudo', 'eval', 'exec',
            'とりあえず', 'TODO', 'FIXME', 'hack'
        ]
        
        # 先頭500文字は必ず含める
        optimized = content[:500]
        
        # キーワード周辺のテキストを抽出
        for keyword in important_keywords:
            idx = content.lower().find(keyword.lower())
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(content), idx + 50)
                optimized += " " + content[start:end]
        
        # 末尾200文字を追加
        if len(content) > 200:
            optimized += " " + content[-200:]
        
        return optimized[:max_length]
    
    def get_performance_stats(self) -> Dict:
        """パフォーマンス統計を取得"""
        total_queries = self.stats['cache_hits'] + self.stats['cache_misses']
        cache_hit_rate = (self.stats['cache_hits'] / total_queries * 100) if total_queries > 0 else 0
        
        return {
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'total_queries': total_queries,
            'pattern_matches': self.stats['pattern_matches'],
            'skip_cache_hits': self.stats['skip_cache_hits'],
            'compiled_patterns': len(self.compiled_patterns)
        }
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.pattern_cache.clear()
        self.skip_cache.clear()
        self.stats = {key: 0 for key in self.stats.keys()}

# グローバルインスタンス（シングルトン）
_optimizer_instance = None

def get_optimizer() -> PerformanceOptimizer:
    """最適化エンジンのシングルトンインスタンスを取得"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = PerformanceOptimizer()
    return _optimizer_instance

if __name__ == "__main__":
    # パフォーマンステスト
    optimizer = PerformanceOptimizer()
    
    test_patterns = {
        r"(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}": "ハードコードされたAPIシークレット",
        r"rm\s+-rf\s+/": "危険な再帰的削除コマンド",
        r"とりあえず|暫定対応": "バンドエイド修正"
    }
    
    test_content = "sk_live_abc123def456ghi789jkl012mno345"
    
    start_time = time.time()
    for i in range(1000):
        result = optimizer.analyze_with_cache(test_content, test_patterns, "CRITICAL")
    end_time = time.time()
    
    print(f"1000回実行時間: {(end_time - start_time)*1000:.2f}ms")
    print(f"パフォーマンス統計: {optimizer.get_performance_stats()}")
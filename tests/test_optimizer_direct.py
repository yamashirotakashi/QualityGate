#!/usr/bin/env python3
"""
パフォーマンス最適化エンジンの直接テスト
"""

import sys
sys.path.insert(0, '/mnt/c/Users/tky99/dev/qualitygate/scripts')

from scripts.performance_optimizer import get_optimizer

def test_direct_matching():
    optimizer = get_optimizer()
    
    test_patterns = {
        r"(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}": "ハードコードされたAPIシークレット",
        r"とりあえず|暫定対応|一時的": "バンドエイド修正"
    }
    
    test_cases = [
        "sk_live_abc123def456ghi789jkl012mno345",
        "とりあえずこれで修正"
    ]
    
    for test_input in test_cases:
        pattern, message = optimizer.fast_pattern_match(test_input, test_patterns)
        print(f"入力: {test_input}")
        print(f"結果: pattern='{pattern}', message='{message}'")
        print()

if __name__ == "__main__":
    test_direct_matching()
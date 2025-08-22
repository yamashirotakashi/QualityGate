#!/usr/bin/env python3
"""
QualityGate - Severity-Based Pattern Analyzer
Phase 1: Critical patterns with exit code 2 blocking
"""

import re
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

class SeverityAnalyzer:
    """Severity-based pattern analysis for QualityGate"""
    
    def __init__(self):
        # Resolve config path with backward-compatible strategy
        # 1) QUALITYGATE_ROOT env
        # 2) Relative to this file (../config/patterns.json)
        # 3) Legacy absolute fallback
        env_root = os.environ.get("QUALITYGATE_ROOT")
        if env_root and Path(env_root).exists():
            base = Path(env_root)
        else:
            base = Path(__file__).resolve().parents[1]
        default_config = base / "config" / "patterns.json"
        legacy_config = Path("/mnt/c/Users/tky99/dev/qualitygate/config/patterns.json")
        self.config_path = default_config if default_config.exists() else legacy_config
        self.analysis_rules = self._load_analysis_rules()
        
    def _load_analysis_rules(self) -> Dict[str, Dict]:
        """Load analysis rules from config or use defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return self._convert_config_to_patterns(config)
            except Exception:
                pass
        
        # Default rules - Phase 1 focus on security-critical patterns
        return {
            'CRITICAL': {
                # Hardcoded secrets (API keys, tokens)
                r"(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}": "ハードコードされたAPIシークレットが検出されました",
                r"AKIA[0-9A-Z]{16}": "ハードコードされたAWSアクセスキーIDが検出されました",
                r"AIza[0-9A-Za-z\\-_]{35}": "ハードコードされたGoogle APIキーが検出されました",
                r"xox[baprs]-[0-9a-zA-Z-]{10,48}": "ハードコードされたSlackトークンが検出されました",
                r"ghp_[0-9a-zA-Z]{36}": "ハードコードされたGitHubパーソナルアクセストークンが検出されました",
                
                # Dangerous operations
                r"rm\s+-rf\s+/": "危険な再帰的削除コマンドが検出されました",
                r"sudo\s+rm\s+-rf": "危険なsudo削除コマンドが検出されました",
                r"DROP\s+DATABASE": "直接的なデータベース削除操作が検出されました",
                r"DELETE\s+FROM\s+\w+\s*(?:;|$)": "フィルタなしのDELETE操作が検出されました",
                
                # Security vulnerabilities
                r"eval\s*\(": "直接的なeval()使用が検出されました",
                r"exec\s*\(": "直接的なexec()使用が検出されました",
                r"os\.system\s*\(": "直接的なos.system()使用が検出されました",
                r"subprocess\.call\s*\([^)]*shell\s*=\s*True": "シェルインジェクション脆弱性が検出されました",
            },
            'HIGH': {
                # Band-aid fixes (Japanese)
                r"とりあえず|暫定対応|一時的|仮対応": "バンドエイド修正の可能性が検出されました",
                
                # Band-aid fixes (English)
                r"\b(temporary|temp|quick.?fix|hack|workaround)\b": "バンドエイド修正の可能性が検出されました",
                
                # TODOs without context
                r"TODO(?!\s*\([^)]+\))": "担当者・コンテキストなしのTODOが検出されました",
                r"FIXME(?!\s*\([^)]+\))": "担当者・コンテキストなしのFIXMEが検出されました",
                r"XXX(?!\s*\([^)]+\))": "コンテキストなしのXXXマーカーが検出されました",
                
                # Hardcoded values
                r"localhost:\d{4,5}": "ハードコードされたlocalhostURLが検出されました",
                r"127\.0\.0\.1:\d{4,5}": "ハードコードされたlocalhostIPが検出されました",
                r"http://[^/]+\.(com|org|net)": "ハードコードされた本番URLが検出されました",
                
                # Missing error handling
                r"except\s*:\s*pass": "サイレント例外処理が検出されました",
                r"catch\s*\(\s*\)\s*\{": "空のcatchブロックが検出されました",
            },
            'INFO': {
                # Minor style issues
                r"console\.log": "デバッグ用console.logが検出されました",
                r"print\s*\(.*debug": "デバッグ用print文が検出されました",
            }
        }
    
    def _convert_config_to_patterns(self, config: Dict) -> Dict[str, Dict]:
        """Convert JSON config format to flat pattern dictionary"""
        result = {}
        
        for severity in ['CRITICAL', 'HIGH', 'INFO']:
            if severity in config:
                result[severity] = {}
                severity_data = config[severity]
                
                if isinstance(severity_data, dict):
                    for category, category_data in severity_data.items():
                        if isinstance(category_data, dict) and 'patterns' in category_data:
                            # Merge patterns from this category
                            result[severity].update(category_data['patterns'])
        
        return result
    
    def analyze(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Analyze content and return highest severity finding
        
        Returns:
            Dict with 'severity', 'message', 'pattern' or None if no issues
        """
        # Start with highest severity and work down
        for severity in ['CRITICAL', 'HIGH', 'INFO']:
            rules = self.analysis_rules.get(severity, {})
            
            for pattern_str, message in rules.items():
                try:
                    pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                    if pattern.search(content):
                        return {
                            'severity': severity,
                            'message': message,
                            'pattern': pattern_str
                        }
                except re.error:
                    # Skip invalid regex patterns
                    continue
        
        return None
    
    def should_block(self, severity: str) -> bool:
        """Determine if severity level should block execution"""
        return severity == 'CRITICAL'
    
    def get_action_for_severity(self, severity: str) -> Dict[str, Any]:
        """Get action configuration for severity level"""
        actions = {
            'CRITICAL': {
                'block': True,
                'exit_code': 2,
                'delay': 0,
                'emoji': '🚫',
                'prefix': '重大'
            },
            'HIGH': {
                'block': False,
                'exit_code': 0,
                'delay': 2,
                'emoji': '⚠️',
                'prefix': '警告'
            },
            'INFO': {
                'block': False,
                'exit_code': 0,
                'delay': 0,
                'emoji': 'ℹ️',
                'prefix': '情報'
            }
        }
        return actions.get(severity, actions['INFO'])

def check_bypass_conditions() -> bool:
    """Check if quality gates should be bypassed"""
    bypass_vars = [
        'BYPASS_DESIGN_HOOK',
        'QUALITYGATE_DISABLED',
        'EMERGENCY_BYPASS'
    ]
    
    for var in bypass_vars:
        if os.environ.get(var, '').lower() in ['1', 'true', 'yes']:
            print(f"🔓 QualityGate {var} によりバイパスされました")
            return True
    
    return False

def main():
    """Main entry point for severity analyzer"""
    # Check for bypass conditions first
    if check_bypass_conditions():
        return 0
    
    # Get input content
    if len(sys.argv) < 2:
        return 0  # No content to analyze
    
    content = " ".join(sys.argv[1:])
    
    # Also check environment variables from hooks
    hook_command = os.environ.get("CLAUDE_HOOK_COMMAND", "")
    hook_message = os.environ.get("CLAUDE_HOOK_MESSAGE", "")
    
    # Combine all content for analysis
    full_content = f"{content} {hook_command} {hook_message}"
    
    # Analyze content
    analyzer = SeverityAnalyzer()
    finding = analyzer.analyze(full_content)
    
    if finding:
        severity = finding['severity']
        message = finding['message']
        action = analyzer.get_action_for_severity(severity)
        
        # Display finding
        print(f"{action['emoji']} {action['prefix']}: {message}", file=sys.stderr)
        
        # Apply delay if configured
        if action['delay'] > 0:
            print(f"⏱️  {action['delay']}秒間停止しています...", file=sys.stderr)
            time.sleep(action['delay'])
        
        # Return appropriate exit code
        if action['block']:
            print("🚫 重大な品質違反により実行をブロックしました", file=sys.stderr)
            return action['exit_code']
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

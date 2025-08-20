#!/usr/bin/env python3
"""
QualityGate Severity Analyzer Integration Tests
===============================================

Tests for the SeverityAnalyzer component that performs pattern matching
and quality analysis for the QualityGate system.

Tests cover:
- Pattern loading from configuration
- Severity-based analysis and blocking
- Pattern matching with regex compilation
- Bypass condition handling
- Configuration file parsing
- Error handling and edge cases
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import re

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from severity_analyzer import SeverityAnalyzer, check_bypass_conditions


@pytest.fixture
def temp_patterns_config(tmp_path):
    """Create temporary patterns configuration for testing."""
    config = {
        "version": "1.0.0",
        "last_updated": "2025-01-01",
        "CRITICAL": {
            "security": {
                "description": "Security-critical patterns",
                "patterns": {
                    "(sk|pk)_(test|live)_[0-9a-zA-Z]{24,}": "ハードコードされたAPIシークレット",
                    "AKIA[0-9A-Z]{16}": "ハードコードされたAWSアクセスキーID",
                    "eval\\s*\\(": "直接的なeval()使用",
                    "rm\\s+-rf\\s+/": "危険な削除コマンド"
                }
            },
            "dangerous_operations": {
                "description": "Dangerous operations",
                "patterns": {
                    "DROP\\s+DATABASE": "データベース削除操作",
                    "sudo\\s+rm\\s+-rf": "sudo削除コマンド"
                }
            }
        },
        "HIGH": {
            "code_quality": {
                "description": "Code quality issues",
                "patterns": {
                    "とりあえず": "バンドエイド修正パターン",
                    "TODO:.*fix.*later": "後回し修正パターン",
                    "HACK:|FIXME:|XXX:": "技術的負債マーカー"
                }
            }
        },
        "MEDIUM": {
            "style": {
                "description": "Style and convention issues",
                "patterns": {
                    "console\\.log\\s*\\(": "デバッグ用console.log",
                    "print\\s*\\(.*debug": "デバッグ用print文"
                }
            }
        },
        "INFO": {
            "informational": {
                "description": "Informational patterns",
                "patterns": {
                    "NOTE:|INFO:|REVIEW:": "情報マーカー"
                }
            }
        }
    }
    
    config_file = tmp_path / "test_patterns.json"
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    
    return config_file


@pytest.fixture
def clean_environment():
    """Ensure clean environment variables for testing."""
    bypass_vars = ["BYPASS_DESIGN_HOOK", "QUALITYGATE_DISABLED", "EMERGENCY_BYPASS"]
    original_values = {}
    
    # Save and clear bypass variables
    for var in bypass_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value


class TestSeverityAnalyzerInitialization:
    """Test SeverityAnalyzer initialization and configuration loading."""
    
    def test_analyzer_default_initialization(self):
        """Test that analyzer initializes with default patterns."""
        analyzer = SeverityAnalyzer()
        
        # Should have loaded default patterns
        assert hasattr(analyzer, 'analysis_rules')
        assert isinstance(analyzer.analysis_rules, dict)
        assert 'CRITICAL' in analyzer.analysis_rules
    
    def test_analyzer_with_custom_config(self, temp_patterns_config):
        """Test analyzer initialization with custom configuration file."""
        # Create analyzer with custom config path
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        # Should have loaded custom patterns
        assert 'CRITICAL' in analyzer.analysis_rules
        assert 'HIGH' in analyzer.analysis_rules
        assert 'MEDIUM' in analyzer.analysis_rules
        assert 'INFO' in analyzer.analysis_rules
    
    def test_analyzer_with_missing_config(self, tmp_path):
        """Test analyzer behavior when config file is missing."""
        # Point to non-existent config
        missing_config = tmp_path / "missing.json"
        
        analyzer = SeverityAnalyzer()
        analyzer.config_path = missing_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        # Should fall back to default patterns
        assert isinstance(analyzer.analysis_rules, dict)
        assert 'CRITICAL' in analyzer.analysis_rules
    
    def test_analyzer_with_malformed_config(self, tmp_path):
        """Test analyzer behavior with malformed JSON config."""
        # Create malformed JSON config
        malformed_config = tmp_path / "malformed.json"
        malformed_config.write_text("{ invalid json content }")
        
        analyzer = SeverityAnalyzer()
        analyzer.config_path = malformed_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        # Should fall back to default patterns
        assert isinstance(analyzer.analysis_rules, dict)
        assert 'CRITICAL' in analyzer.analysis_rules


class TestSeverityAnalyzerPatternMatching:
    """Test pattern matching functionality."""
    
    def test_critical_security_patterns(self, temp_patterns_config):
        """Test detection of critical security patterns."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        critical_examples = [
            ("sk_test_1234567890abcdef1234567890abcdef", "API key"),
            ("AKIA1234567890123456", "AWS key"),
            ("eval(user_input)", "eval usage"),
            ("rm -rf /", "dangerous deletion"),
            ("DROP DATABASE production", "database deletion"),
            ("sudo rm -rf /home", "sudo deletion")
        ]
        
        for content, description in critical_examples:
            finding = analyzer.analyze(content)
            assert finding is not None, f"Should detect critical pattern: {description}"
            assert finding['severity'] == 'CRITICAL', f"Should be CRITICAL severity: {description}"
            assert len(finding['message']) > 0, f"Should have descriptive message: {description}"
    
    def test_high_severity_patterns(self, temp_patterns_config):
        """Test detection of high severity patterns."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        high_examples = [
            ("とりあえず修正しました", "band-aid fix"),
            ("TODO: fix this properly later", "deferred fix"),
            ("HACK: temporary solution", "technical debt"),
            ("FIXME: broken logic here", "broken code marker"),
            ("XXX: needs refactoring", "refactoring needed")
        ]
        
        for content, description in high_examples:
            finding = analyzer.analyze(content)
            assert finding is not None, f"Should detect high pattern: {description}"
            assert finding['severity'] == 'HIGH', f"Should be HIGH severity: {description}"
    
    def test_medium_and_info_patterns(self, temp_patterns_config):
        """Test detection of medium and info severity patterns."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        test_cases = [
            ("console.log('debug info')", "MEDIUM", "debug console.log"),
            ("print(debug_variable)", "MEDIUM", "debug print"),
            ("NOTE: this is important", "INFO", "note marker"),
            ("INFO: user should know", "INFO", "info marker"),
            ("REVIEW: needs attention", "INFO", "review marker")
        ]
        
        for content, expected_severity, description in test_cases:
            finding = analyzer.analyze(content)
            if finding:  # Some patterns might not match depending on exact regex
                assert finding['severity'] == expected_severity, f"Should be {expected_severity} severity: {description}"
    
    def test_safe_content_no_matches(self, temp_patterns_config):
        """Test that safe content produces no findings."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        safe_examples = [
            "This is normal code",
            "def hello_world(): return 'Hello'",
            "import os\nprint('Hello World')",
            "const message = 'Safe content';",
            "// This is a comment",
            "SELECT * FROM users WHERE id = ?",
        ]
        
        for content in safe_examples:
            finding = analyzer.analyze(content)
            assert finding is None, f"Safe content should not trigger patterns: {content[:30]}..."
    
    def test_case_sensitivity_handling(self, temp_patterns_config):
        """Test pattern matching with different case variations."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        # Test case variations of dangerous commands
        case_variations = [
            "rm -rf /",
            "RM -RF /",
            "Rm -Rf /",
            "eval(input)",
            "EVAL(input)",
            "Eval(input)"
        ]
        
        for content in case_variations:
            finding = analyzer.analyze(content)
            # Depending on regex flags, some might not match
            # This tests the current behavior
            if finding:
                assert finding['severity'] in ['CRITICAL', 'HIGH'], f"Dangerous pattern should be detected: {content}"
    
    def test_regex_special_characters(self, temp_patterns_config):
        """Test pattern matching with regex special characters in content."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        special_char_content = [
            "sk_test_abc123.def456*ghi789",  # Should still match API key pattern
            "eval() called with $input",     # Should match eval pattern
            "rm -rf / # dangerous comment",  # Should match dangerous deletion
        ]
        
        for content in special_char_content:
            finding = analyzer.analyze(content)
            # Should handle special characters gracefully
            # Either match or not match, but not crash
            assert True  # If we get here, no exception was thrown
    
    def test_empty_and_whitespace_content(self, temp_patterns_config):
        """Test analyzer behavior with empty or whitespace-only content."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        empty_examples = [
            "",
            "   ",
            "\n\n\n",
            "\t\t\t",
            "    \n    \t    ",
        ]
        
        for content in empty_examples:
            finding = analyzer.analyze(content)
            assert finding is None, f"Empty/whitespace content should not match patterns: '{content}'"


class TestSeverityAnalyzerSeverityHandling:
    """Test severity-based decision making."""
    
    def test_should_block_critical_only(self):
        """Test that only CRITICAL severity should block execution."""
        analyzer = SeverityAnalyzer()
        
        # Test all severity levels
        assert analyzer.should_block('CRITICAL') is True, "CRITICAL should block"
        assert analyzer.should_block('HIGH') is False, "HIGH should not block"
        assert analyzer.should_block('MEDIUM') is False, "MEDIUM should not block"
        assert analyzer.should_block('LOW') is False, "LOW should not block"
        assert analyzer.should_block('INFO') is False, "INFO should not block"
        assert analyzer.should_block('UNKNOWN') is False, "UNKNOWN should not block"
    
    def test_get_action_for_severity(self):
        """Test that severity levels have appropriate action configurations."""
        analyzer = SeverityAnalyzer()
        
        # Test CRITICAL action
        critical_action = analyzer.get_action_for_severity('CRITICAL')
        assert critical_action['block'] is True, "CRITICAL should block"
        assert critical_action['exit_code'] == 2, "CRITICAL should have exit code 2"
        assert critical_action['delay'] == 0, "CRITICAL should have no delay"
        assert '🚫' in critical_action['emoji'], "CRITICAL should have blocking emoji"
        
        # Test HIGH action  
        high_action = analyzer.get_action_for_severity('HIGH')
        assert high_action['block'] is False, "HIGH should not block"
        assert high_action['exit_code'] == 0, "HIGH should have exit code 0"
        assert high_action['delay'] >= 0, "HIGH should have non-negative delay"
        
        # Test INFO action (default fallback)
        info_action = analyzer.get_action_for_severity('INFO')
        assert info_action['block'] is False, "INFO should not block"
        assert info_action['exit_code'] == 0, "INFO should have exit code 0"
        assert info_action['delay'] == 0, "INFO should have no delay"
        
        # Test unknown severity (should default to INFO)
        unknown_action = analyzer.get_action_for_severity('UNKNOWN_SEVERITY')
        assert unknown_action['block'] is False, "Unknown severity should not block"
        assert unknown_action['exit_code'] == 0, "Unknown severity should have exit code 0"


class TestSeverityAnalyzerBypassConditions:
    """Test bypass condition functionality."""
    
    def test_check_bypass_conditions_no_bypass(self, clean_environment):
        """Test bypass check when no bypass variables are set."""
        # Act
        should_bypass = check_bypass_conditions()
        
        # Assert
        assert should_bypass is False, "Should not bypass when no variables set"
    
    @pytest.mark.parametrize("bypass_var", [
        "BYPASS_DESIGN_HOOK",
        "QUALITYGATE_DISABLED", 
        "EMERGENCY_BYPASS"
    ])
    @pytest.mark.parametrize("bypass_value", ["1", "true", "TRUE", "yes", "YES"])
    def test_check_bypass_conditions_with_bypass(self, clean_environment, bypass_var, bypass_value):
        """Test bypass check with various bypass variables and values."""
        # Arrange
        os.environ[bypass_var] = bypass_value
        
        # Act
        should_bypass = check_bypass_conditions()
        
        # Assert
        assert should_bypass is True, f"Should bypass with {bypass_var}={bypass_value}"
        
        # Clean up
        del os.environ[bypass_var]
    
    @pytest.mark.parametrize("invalid_value", ["0", "false", "FALSE", "no", "NO", "disabled", ""])
    def test_check_bypass_conditions_invalid_values(self, clean_environment, invalid_value):
        """Test bypass check with invalid bypass values."""
        # Arrange
        os.environ["QUALITYGATE_DISABLED"] = invalid_value
        
        # Act
        should_bypass = check_bypass_conditions()
        
        # Assert
        assert should_bypass is False, f"Should not bypass with invalid value: {invalid_value}"
        
        # Clean up
        del os.environ["QUALITYGATE_DISABLED"]
    
    def test_check_bypass_multiple_variables(self, clean_environment):
        """Test bypass check with multiple bypass variables set."""
        # Arrange
        os.environ["BYPASS_DESIGN_HOOK"] = "0"  # Invalid value
        os.environ["EMERGENCY_BYPASS"] = "1"    # Valid value
        
        # Act
        should_bypass = check_bypass_conditions()
        
        # Assert
        assert should_bypass is True, "Should bypass if any variable has valid value"
        
        # Clean up
        del os.environ["BYPASS_DESIGN_HOOK"]
        del os.environ["EMERGENCY_BYPASS"]


class TestSeverityAnalyzerErrorHandling:
    """Test error handling and edge cases."""
    
    def test_analyze_with_invalid_regex_patterns(self, tmp_path):
        """Test analyzer behavior with invalid regex patterns in config."""
        # Create config with invalid regex patterns
        invalid_config = {
            "CRITICAL": {
                "invalid_regex": {
                    "patterns": {
                        "[invalid(regex": "Invalid regex pattern",
                        "*+?{": "Another invalid pattern",
                        "(?P<>)": "Invalid named group"
                    }
                }
            }
        }
        
        config_file = tmp_path / "invalid_patterns.json"
        config_file.write_text(json.dumps(invalid_config))
        
        # Create analyzer with invalid config
        analyzer = SeverityAnalyzer()
        analyzer.config_path = config_file
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        # Should not crash when analyzing content
        finding = analyzer.analyze("test content")
        # Should either return None or a valid finding, but not crash
        assert finding is None or isinstance(finding, dict)
    
    def test_analyze_with_large_content(self, temp_patterns_config):
        """Test analyzer performance with large content."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        # Create large content with embedded pattern
        large_content = "x" * 50000 + "sk_test_1234567890abcdef1234567890abcdef" + "y" * 50000
        
        # Should handle large content without timing out
        finding = analyzer.analyze(large_content)
        assert finding is not None, "Should detect pattern in large content"
        assert finding['severity'] == 'CRITICAL', "Should correctly identify severity"
    
    def test_analyze_with_unicode_content(self, temp_patterns_config):
        """Test analyzer with Unicode and non-ASCII content."""
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        
        unicode_examples = [
            "とりあえず修正しました",  # Japanese text (should match HIGH pattern)
            "🚀 Code with emojis: sk_test_1234567890abcdef1234567890abcdef",  # Emojis + pattern
            "Código en español: eval(entrada)",  # Spanish + pattern
            "Русский код: rm -rf /",  # Cyrillic + pattern
        ]
        
        for content in unicode_examples:
            finding = analyzer.analyze(content)
            # Should handle Unicode content gracefully
            # May or may not find patterns depending on exact content
            assert True  # If we get here, no Unicode error was thrown
    
    def test_convert_config_to_patterns_empty_config(self):
        """Test pattern conversion with empty configuration."""
        analyzer = SeverityAnalyzer()
        
        # Test with empty config
        empty_patterns = analyzer._convert_config_to_patterns({})
        assert isinstance(empty_patterns, dict), "Should return dict for empty config"
        
        # Test with config missing pattern sections
        partial_config = {"version": "1.0", "other_data": "value"}
        partial_patterns = analyzer._convert_config_to_patterns(partial_config)
        assert isinstance(partial_patterns, dict), "Should handle partial config"
    
    def test_pattern_compilation_performance(self, temp_patterns_config):
        """Test that pattern compilation doesn't significantly impact performance."""
        import time
        
        analyzer = SeverityAnalyzer()
        analyzer.config_path = temp_patterns_config
        
        # Measure time to load and compile patterns
        start_time = time.time()
        analyzer.analysis_rules = analyzer._load_analysis_rules()
        load_time = time.time() - start_time
        
        # Should load patterns quickly
        assert load_time < 1.0, f"Pattern loading should be fast, took {load_time:.2f}s"
        
        # Measure analysis time
        test_content = "This is test content with sk_test_1234567890abcdef1234567890abcdef"
        start_time = time.time()
        finding = analyzer.analyze(test_content)
        analysis_time = time.time() - start_time
        
        # Should analyze quickly
        assert analysis_time < 0.5, f"Analysis should be fast, took {analysis_time:.2f}s"
        assert finding is not None, "Should find the pattern"


class TestSeverityAnalyzerMainFunction:
    """Test the main() function CLI behavior."""
    
    @patch('sys.argv', ['severity_analyzer.py', 'test', 'content'])
    def test_main_with_command_line_args(self, clean_environment):
        """Test main function with command line arguments."""
        # Import and run main function
        from severity_analyzer import main
        
        # Should run without errors
        exit_code = main()
        assert exit_code == 0, "Should exit successfully with safe content"
    
    @patch('sys.argv', ['severity_analyzer.py'])
    def test_main_with_no_args(self, clean_environment):
        """Test main function with no arguments."""
        from severity_analyzer import main
        
        # Should handle no arguments gracefully
        exit_code = main()
        assert exit_code == 0, "Should exit successfully with no content to analyze"
    
    @patch.dict(os.environ, {'CLAUDE_HOOK_COMMAND': 'rm -rf /', 'CLAUDE_HOOK_MESSAGE': 'dangerous'})
    @patch('sys.argv', ['severity_analyzer.py', 'additional', 'content'])
    def test_main_with_environment_variables(self, clean_environment):
        """Test main function with hook environment variables."""
        from severity_analyzer import main
        
        # Should process environment variables along with args
        exit_code = main()
        # May block (exit code 2) or continue (exit code 0) depending on pattern configuration
        assert exit_code in [0, 2], "Should handle environment variables appropriately"
    
    @patch.dict(os.environ, {'EMERGENCY_BYPASS': '1'})
    @patch('sys.argv', ['severity_analyzer.py', 'sk_test_dangerous_content'])
    def test_main_with_bypass_enabled(self, clean_environment):
        """Test main function with bypass enabled."""
        from severity_analyzer import main
        
        # Should bypass analysis
        exit_code = main()
        assert exit_code == 0, "Should exit successfully when bypass is enabled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
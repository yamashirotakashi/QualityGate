#!/usr/bin/env python3
"""
QualityGate Phase 3B: Enterprise Components Independent Testing
Core Layer依存性を回避したEnterprise Layer単体テスト
"""

import asyncio
import time
import json
from typing import Dict, Any

# Enterprise Layer Components Import (Core Layer非依存)
from enterprise.models.monitoring import PerformanceMonitor, MetricType
from enterprise.integrations.bus import IntegrationBus, IntegrationType
from enterprise.auth.manager import AuthenticationManager
from enterprise.security.middleware import OWASPMiddleware
from enterprise.database.connection import DatabaseManager


class EnterpriseComponentsTester:
    """Enterprise Layer独立コンポーネントテスター"""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    async def run_all_tests(self):
        """全テスト実行"""
        print("🚀 Starting QualityGate Phase 3B Enterprise Components Tests")
        print("=" * 80)
        
        start_time = time.time()
        
        # テスト実行
        await self.test_performance_monitoring()
        await self.test_integration_bus()
        await self.test_authentication_system()
        await self.test_security_framework()
        await self.test_database_operations()
        
        # 結果集計
        total_time = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")
        print(f"Total Time: {total_time:.2f}s")
        
        # 詳細結果
        print(f"\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            duration = result["duration"]
            print(f"  {test_name}: {status} ({duration:.2f}s)")
            
            if not result["passed"] and "error" in result:
                print(f"    Error: {result['error']}")
        
        # パフォーマンス制約チェック
        print(f"\n⚡ Performance Constraints Check:")
        performance_violations = [
            result for result in self.test_results.values()
            if result.get("performance_violation", False)
        ]
        
        if performance_violations:
            print(f"  ⚠️ {len(performance_violations)} performance constraint violations detected")
        else:
            print(f"  ✅ All performance constraints met")
        
        return self.passed_tests == self.total_tests
    
    async def test_performance_monitoring(self):
        """パフォーマンス監視テスト"""
        test_name = "Performance Monitoring"
        start_time = time.time()
        
        try:
            print(f"\n🧪 Testing {test_name}...")
            
            monitor = PerformanceMonitor()
            
            # メトリクス記録テスト
            await monitor.record_metric(MetricType.API_RESPONSE_TIME, 45.0, tenant_id="test-tenant")
            await monitor.record_metric(MetricType.AUTH_PROCESSING_TIME, 25.0, tenant_id="test-tenant")
            await monitor.record_metric(MetricType.DB_QUERY_TIME, 15.0, tenant_id="test-tenant")
            
            # 制約違反テスト
            await monitor.record_metric(MetricType.API_RESPONSE_TIME, 150.0, tenant_id="test-tenant")  # 制約違反
            
            # 統計取得テスト
            summary = monitor.get_performance_summary()
            compliance = monitor.get_constraint_compliance()
            violations = monitor.get_recent_violations(10)
            
            # 検証
            assert summary["total_metrics"] > 0, "No metrics recorded"
            assert summary["total_violations"] > 0, "No violations detected"
            assert len(violations) > 0, "No violations in history"
            
            self._record_test_result(test_name, True, time.time() - start_time)
            print(f"  ✅ Performance monitoring tests passed")
            print(f"  📊 Metrics: {summary['total_metrics']}, Violations: {summary['total_violations']}")
            
        except Exception as e:
            self._record_test_result(test_name, False, time.time() - start_time, str(e))
            print(f"  ❌ Performance monitoring test failed: {e}")
    
    async def test_integration_bus(self):
        """統合バステスト"""
        test_name = "Integration Bus"
        start_time = time.time()
        
        try:
            print(f"\n🧪 Testing {test_name}...")
            
            bus = IntegrationBus()
            
            # Slack統合登録テスト
            slack_config = {
                "webhook_url": "https://hooks.slack.com/services/TEST/TEST/TEST"
            }
            
            success = await bus.register_integration(
                "test-slack",
                IntegrationType.SLACK,
                "Test Slack Integration",
                slack_config,
                "test-tenant"
            )
            
            assert success, "Slack integration registration failed"
            
            # 通知送信テスト
            violation_data = {
                "severity": "CRITICAL",
                "pattern": "Test Pattern",
                "file_path": "test.py",
                "blocked": True
            }
            
            results = await bus.send_quality_violation_alert(violation_data, "test-tenant")
            
            # ステータス確認テスト
            status = bus.get_integration_status()
            
            assert len(status["integrations"]) > 0, "No integrations registered"
            
            self._record_test_result(test_name, True, time.time() - start_time)
            print(f"  ✅ Integration bus tests passed")
            print(f"  🔗 Active integrations: {status['statistics']['active_integrations']}")
            
        except Exception as e:
            self._record_test_result(test_name, False, time.time() - start_time, str(e))
            print(f"  ❌ Integration bus test failed: {e}")
    
    async def test_authentication_system(self):
        """認証システムテスト"""
        test_name = "Authentication System"
        start_time = time.time()
        
        try:
            print(f"\n🧪 Testing {test_name}...")
            
            auth_manager = AuthenticationManager()
            
            # パスワードハッシュ化テスト
            password = "test_password_123"
            hashed = auth_manager.hash_password(password)
            
            assert hashed != password, "Password not hashed"
            assert auth_manager.verify_password(password, hashed), "Password verification failed"
            
            # JWT トークン作成テスト（MockUser使用）
            mock_user = type('User', (), {
                'id': 'test-user-001',
                'email': 'test@example.com'
            })()
            
            mock_membership = type('Membership', (), {
                'tenant_id': 'test-tenant',
                'role_id': 'test-role'
            })()
            
            token = auth_manager.create_access_token(mock_user, mock_membership)
            
            assert token, "JWT token creation failed"
            
            # トークン検証テスト
            payload = await auth_manager.verify_token(token)
            
            assert payload, "JWT token verification failed"
            assert payload["sub"] == "test-user-001", "Token payload incorrect"
            
            # API Key生成テスト
            api_key, key_hash = auth_manager.generate_api_key(mock_user, "test-tenant", "Test Key")
            
            assert api_key.startswith("qg_live_"), "API key format incorrect"
            assert len(api_key) > 32, "API key too short"
            
            # 統計取得テスト
            stats = auth_manager.get_auth_stats()
            
            self._record_test_result(test_name, True, time.time() - start_time)
            print(f"  ✅ Authentication system tests passed")
            print(f"  🔐 Token created and verified successfully")
            
        except Exception as e:
            self._record_test_result(test_name, False, time.time() - start_time, str(e))
            print(f"  ❌ Authentication system test failed: {e}")
    
    async def test_security_framework(self):
        """セキュリティフレームワークテスト"""
        test_name = "Security Framework"
        start_time = time.time()
        
        try:
            print(f"\n🧪 Testing {test_name}...")
            
            # Mock FastAPIアプリケーション作成
            from fastapi import FastAPI
            
            app = FastAPI()
            owasp_middleware = OWASPMiddleware(app)
            
            # セキュリティ検証テスト用のMockリクエスト
            class MockRequest:
                def __init__(self, url, method="GET", headers=None, query=""):
                    self.url = type('URL', (), {'path': url, 'query': query})()
                    self.method = method
                    self.headers = headers or {}
                    self.client = type('Client', (), {'host': '127.0.0.1'})()
                
                async def body(self):
                    return b"test body"
            
            # 正常リクエストテスト
            normal_request = MockRequest("/api/v1/health")
            result = await owasp_middleware._validate_request_security(normal_request)
            
            assert result["safe"], "Normal request flagged as unsafe"
            
            # インジェクション攻撃検出テスト
            injection_request = MockRequest("/api/v1/test", query="id=1' OR '1'='1")
            result = await owasp_middleware._validate_request_security(injection_request)
            
            assert not result["safe"], "Injection attack not detected"
            assert result["category"] == "A03", "Wrong OWASP category"
            
            # セキュリティ統計取得テスト
            stats = owasp_middleware.get_security_stats()
            
            assert stats["total_requests"] > 0, "No security requests recorded"
            
            self._record_test_result(test_name, True, time.time() - start_time)
            print(f"  ✅ Security framework tests passed")
            print(f"  🛡️ OWASP middleware functioning correctly")
            
        except Exception as e:
            self._record_test_result(test_name, False, time.time() - start_time, str(e))
            print(f"  ❌ Security framework test failed: {e}")
    
    async def test_database_operations(self):
        """データベース操作テスト"""
        test_name = "Database Operations"
        start_time = time.time()
        
        try:
            print(f"\n🧪 Testing {test_name}...")
            
            db_manager = DatabaseManager()
            
            # データベース初期化テスト
            await db_manager.initialize()
            
            assert db_manager.is_connected(), "Database not connected"
            
            # データベース統計取得テスト
            stats = await db_manager.get_database_stats()
            
            assert stats["status"] == "connected", "Database status incorrect"
            
            # サンプルテナント作成テスト
            tenant_id = await db_manager.create_sample_tenant("test-tenant-001")
            
            assert tenant_id, "Sample tenant creation failed"
            
            # データベース接続クローズテスト
            await db_manager.close()
            
            self._record_test_result(test_name, True, time.time() - start_time)
            print(f"  ✅ Database operations tests passed")
            print(f"  💾 Database initialization and operations successful")
            
        except Exception as e:
            self._record_test_result(test_name, False, time.time() - start_time, str(e))
            print(f"  ❌ Database operations test failed: {e}")
    
    def _record_test_result(self, test_name: str, passed: bool, duration: float, error: str = None, **kwargs):
        """テスト結果記録"""
        self.total_tests += 1
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        result = {
            "passed": passed,
            "duration": duration,
            **kwargs
        }
        
        if error:
            result["error"] = error
        
        self.test_results[test_name] = result


async def main():
    """メイン実行"""
    tester = EnterpriseComponentsTester()
    success = await tester.run_all_tests()
    
    if success:
        print(f"\n🎉 All tests passed! QualityGate Phase 3B Enterprise Components are ready.")
        exit(0)
    else:
        print(f"\n💥 Some tests failed. Please review the results above.")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
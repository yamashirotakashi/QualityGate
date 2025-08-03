"""
QualityGate Phase 3B: Enterprise Integration Layer
HFP Architecture Phase 5 - Enterprise Layer Implementation

統合アーキテクチャ:
Core Layer (Phase 3A 6-Engine Architecture) + Enterprise Layer (Phase 3B)
"""

__version__ = "3.0.0-beta.1"
__phase__ = "Phase 3B: Enterprise Integration"

# パフォーマンス制約定義 (既存システムとの統合)
ENTERPRISE_CONSTRAINTS = {
    # API Layer制約
    "API_RESPONSE_MS": 100,        # API応答時間: 100ms以下
    "CONCURRENT_REQUESTS": 1000,   # 並行処理: 1000req/sec対応
    "AUTH_PROCESSING_MS": 50,      # 認証処理: 50ms以下
    "DB_QUERY_MS": 30,            # データベースクエリ: 30ms以下
    
    # 既存システム統合制約 (Phase 3A継承)
    "CORE_REALTIME_MS": 1.5,      # リアルタイム制約: 1.5ms維持
    "HOOK_INTEGRATION_MS": 0.05,  # Hook統合: 0.05ms以下
    "ULTRA_CRITICAL_MS": 0.1,     # 重要パターン: 0.1ms以下
    
    # Enterprise Layer統合制約
    "MULTI_TENANT_OVERHEAD_MS": 5, # Multi-tenant処理オーバーヘッド: 5ms以下
    "SECURITY_VALIDATION_MS": 10,  # セキュリティ検証: 10ms以下
    "ANALYTICS_AGGREGATION_MS": 50, # 分析データ集約: 50ms以下
}

# Enterprise Layer Architecture Definition
ENTERPRISE_ARCHITECTURE = {
    "layers": {
        "api_gateway": {
            "path": "enterprise.api",
            "description": "REST API Gateway & OpenAPI Documentation"
        },
        "authentication": {
            "path": "enterprise.auth", 
            "description": "JWT/OAuth2 Authentication & Multi-tenant Management"
        },
        "database": {
            "path": "enterprise.database",
            "description": "SQLAlchemy ORM & Multi-tenant Data Separation"
        },
        "security": {
            "path": "enterprise.security",
            "description": "OWASP Security Framework & Vulnerability Protection"
        },
        "integrations": {
            "path": "enterprise.integrations",
            "description": "External Tool Integration Bus (Slack, Teams, JIRA)"
        },
        "dashboard": {
            "path": "enterprise.dashboard", 
            "description": "Advanced Analytics Dashboard & Real-time Metrics"
        }
    },
    "integration_points": {
        "core_engines": "scripts/optimized_severity_analyzer.py",
        "hook_system": "hooks/",
        "config_system": "config/",
        "monitoring": "scripts/qualitygate_status.py"
    }
}

# セキュリティ設定
SECURITY_SETTINGS = {
    "owasp_compliance": True,
    "rate_limiting": True,
    "request_validation": True,
    "sql_injection_protection": True,
    "xss_protection": True,
    "csrf_protection": True,
    "headers_security": True
}
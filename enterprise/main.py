#!/usr/bin/env python3
"""
QualityGate Enterprise API Server
Phase 3B: Enterprise Integration - FastAPI Implementation

統合アーキテクチャ:
- Core Layer: 6-Engine Architecture (Phase 3A)
- Enterprise Layer: Multi-tenant API + RBAC + Analytics (Phase 3B)
"""

import time
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer
import uvicorn

# Enterprise Layer Components
from enterprise.auth.middleware import AuthenticationMiddleware, RateLimitMiddleware
from enterprise.security.middleware import SecurityHeadersMiddleware, OWASPMiddleware
from enterprise.database.connection import DatabaseManager
from enterprise.models.monitoring import PerformanceMonitor
from enterprise.integrations.bus import IntegrationBus
from enterprise.api.routers import (
    webhook_router,
    analytics_router, 
    tenant_router,
    security_router,
    integration_router
)

# Core Layer Integration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scripts.optimized_severity_analyzer import OptimizedSeverityAnalyzer


class EnterpriseQualityGateAPI:
    """Enterprise Quality Gate API Application"""
    
    def __init__(self):
        self.core_analyzer = None
        self.db_manager = None
        self.performance_monitor = None
        self.integration_bus = None
        self.startup_time = time.time()
        
        # パフォーマンス制約チェッカー
        self.performance_constraints = {
            "api_response_ms": 100,
            "auth_processing_ms": 50,
            "db_query_ms": 30,
            "core_realtime_ms": 1.5  # Core Layer制約維持
        }
        
    async def initialize_core_integration(self):
        """Core Layer (6-Engine Architecture) 統合初期化"""
        start_time = time.time()
        
        try:
            # Phase 3A Core Layer統合
            self.core_analyzer = OptimizedSeverityAnalyzer()
            
            # データベース接続初期化
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # パフォーマンス監視初期化
            self.performance_monitor = PerformanceMonitor()
            
            # Integration Bus初期化
            self.integration_bus = IntegrationBus()
            
            init_time = (time.time() - start_time) * 1000
            print(f"🚀 Enterprise Layer initialized in {init_time:.2f}ms")
            
            # Core Layer制約チェック
            if init_time > 50:  # Enterprise初期化制約
                print(f"⚠️ WARNING: Initialization time {init_time:.2f}ms exceeds 50ms limit")
                
        except Exception as e:
            print(f"❌ Enterprise Layer initialization failed: {e}")
            raise


# FastAPI Lifecycle Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    enterprise_api = EnterpriseQualityGateAPI()
    await enterprise_api.initialize_core_integration()
    app.state.enterprise_api = enterprise_api
    
    print("🏢 QualityGate Enterprise API Server Started")
    print(f"📊 Core Integration: 6-Engine Architecture")
    print(f"🔒 Security: OWASP + Multi-tenant RBAC")
    print(f"⚡ Performance: <100ms API, <1.5ms Core")
    
    yield
    
    # Shutdown
    if hasattr(app.state, 'enterprise_api') and app.state.enterprise_api.db_manager:
        await app.state.enterprise_api.db_manager.close()
    print("🛑 QualityGate Enterprise API Server Stopped")


# FastAPI Application Setup
app = FastAPI(
    title="QualityGate Enterprise API",
    description="Enterprise Integration Layer for QualityGate AI Learning Edition",
    version="3.0.0-beta.1",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Security Headers Middleware (OWASP Compliance)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(OWASPMiddleware)

# CORS Middleware - Secure Configuration
allowed_origins = os.getenv("QG_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-CSRF-Token"],
)

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Authentication & Rate Limiting Middleware
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware)

# Performance Monitoring Middleware
@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """パフォーマンス監視ミドルウェア"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time"] = str(process_time)
    
    # パフォーマンス制約チェック
    if process_time > 100:  # API応答時間制約
        print(f"⚠️ PERFORMANCE WARNING: {request.url.path} took {process_time:.2f}ms (>100ms limit)")
    
    # Performance Monitor記録
    if hasattr(request.app.state, 'enterprise_api') and request.app.state.enterprise_api.performance_monitor:
        await request.app.state.enterprise_api.performance_monitor.record_request(
            path=request.url.path,
            method=request.method,
            response_time_ms=process_time,
            status_code=response.status_code
        )
    
    return response


# API Router Integration
app.include_router(webhook_router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(tenant_router, prefix="/api/v1/tenants", tags=["tenants"])
app.include_router(security_router, prefix="/api/v1/security", tags=["security"])
app.include_router(integration_router, prefix="/api/v1/integrations", tags=["integrations"])


# Health Check & Status Endpoints
@app.get("/api/v1/health")
async def health_check():
    """システム健全性チェック"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime_seconds": time.time() - app.state.enterprise_api.startup_time if hasattr(app.state, 'enterprise_api') else 0,
        "core_integration": "6-Engine Architecture",
        "enterprise_layer": "Phase 3B Active"
    }


@app.get("/api/v1/status")
async def enterprise_status(request: Request):
    """Enterprise Layer統合ステータス"""
    if not hasattr(request.app.state, 'enterprise_api'):
        raise HTTPException(status_code=503, detail="Enterprise API not initialized")
    
    enterprise_api = request.app.state.enterprise_api
    
    # Core Layer統合ステータス
    core_status = None
    if enterprise_api.core_analyzer:
        # 6-Engine Architecture統計取得
        try:
            core_stats = {
                "ultrafast_enabled": enterprise_api.core_analyzer.ultrafast_enabled,
                "learning_enabled": enterprise_api.core_analyzer.learning_enabled,
                "background_learning_enabled": enterprise_api.core_analyzer.background_learning_enabled,
                "realtime_integration_enabled": enterprise_api.core_analyzer.realtime_integration_enabled,
                "pattern_generation_enabled": enterprise_api.core_analyzer.pattern_generation_enabled
            }
            core_status = "active"
        except Exception as e:
            core_status = f"error: {e}"
            core_stats = {}
    else:
        core_status = "not_initialized"
        core_stats = {}
    
    return {
        "enterprise_layer": {
            "status": "active",
            "version": "3.0.0-beta.1",
            "phase": "Phase 3B: Enterprise Integration"
        },
        "core_layer": {
            "status": core_status,
            "architecture": "6-Engine Architecture",
            "engines": core_stats
        },
        "performance": {
            "constraints": enterprise_api.performance_constraints,
            "uptime_seconds": time.time() - enterprise_api.startup_time
        },
        "database": {
            "status": "connected" if enterprise_api.db_manager and enterprise_api.db_manager.is_connected() else "disconnected"
        }
    }


# Core Layer分析APIエンドポイント
@app.post("/api/v1/analyze")
async def analyze_content(request: Request, content: Dict[str, Any]):
    """Core Layer統合分析API"""
    if not hasattr(request.app.state, 'enterprise_api') or not request.app.state.enterprise_api.core_analyzer:
        raise HTTPException(status_code=503, detail="Core analyzer not available")
    
    start_time = time.time()
    
    try:
        # Core Layer (6-Engine Architecture) 分析実行
        analyzer = request.app.state.enterprise_api.core_analyzer
        
        input_text = content.get("text", "")
        file_type = content.get("file_type", "unknown")
        
        # Phase 3A統合分析実行
        analysis_result = analyzer.analyze_input_optimized(input_text, file_type)
        
        # パフォーマンス制約チェック
        analysis_time = (time.time() - start_time) * 1000
        
        return {
            "analysis": analysis_result,
            "performance": {
                "analysis_time_ms": analysis_time,
                "core_constraint_ms": 1.5,
                "constraint_met": analysis_time <= 1.5
            },
            "enterprise_metadata": {
                "api_version": "3.0.0-beta.1",
                "tenant_id": content.get("tenant_id", "default"),
                "timestamp": time.time()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "enterprise.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
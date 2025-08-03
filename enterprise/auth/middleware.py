#!/usr/bin/env python3
"""
QualityGate Enterprise Authentication Middleware
FastAPI Authentication & Rate Limiting Implementation
"""

import time
import asyncio
from typing import Optional, Dict, Any, List
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from enterprise.auth.manager import AuthenticationManager
from enterprise.database.connection import DatabaseManager


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """認証ミドルウェア"""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_manager = AuthenticationManager()
        self.security = HTTPBearer(auto_error=False)
        
        # パブリックエンドポイント（認証不要）
        self.public_endpoints = {
            "/api/v1/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # パブリックエンドポイントはスキップ
        if request.url.path in self.public_endpoints:
            return await call_next(request)
        
        # 認証情報確認
        auth_result = await self._authenticate_request(request)
        
        if auth_result is None:
            return Response(
                content='{"detail":"Authentication required"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        # リクエストに認証情報を追加
        request.state.user = auth_result["user"]
        request.state.tenant_id = auth_result["tenant_id"]
        request.state.permissions = auth_result["permissions"]
        
        # 処理継続
        response = await call_next(request)
        
        # パフォーマンス監視
        processing_time = (time.time() - start_time) * 1000
        response.headers["X-Auth-Time"] = str(processing_time)
        
        return response
    
    async def _authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """リクエスト認証"""
        # Authorization Header確認
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return None
        
        try:
            if authorization.startswith("Bearer "):
                # JWT Token認証
                token = authorization.split(" ", 1)[1]
                return await self._authenticate_jwt(request, token)
                
            elif authorization.startswith("API-Key "):
                # API Key認証
                api_key = authorization.split(" ", 1)[1]
                return await self._authenticate_api_key(request, api_key)
                
            else:
                return None
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return None
    
    async def _authenticate_jwt(self, request: Request, token: str) -> Optional[Dict[str, Any]]:
        """JWT認証"""
        payload = await self.auth_manager.verify_token(token)
        
        if not payload:
            return None
        
        # データベースからユーザー情報取得
        if hasattr(request.app.state, 'enterprise_api') and request.app.state.enterprise_api.db_manager:
            async with request.app.state.enterprise_api.db_manager.get_async_session() as db:
                # 権限取得
                permissions = await self.auth_manager.get_user_permissions(
                    db, payload["sub"], payload["tenant_id"]
                )
                
                return {
                    "user": {
                        "id": payload["sub"],
                        "email": payload["email"]
                    },
                    "tenant_id": payload["tenant_id"],
                    "permissions": permissions,
                    "auth_type": "jwt"
                }
        
        return None
    
    async def _authenticate_api_key(self, request: Request, api_key: str) -> Optional[Dict[str, Any]]:
        """API Key認証"""
        if hasattr(request.app.state, 'enterprise_api') and request.app.state.enterprise_api.db_manager:
            async with request.app.state.enterprise_api.db_manager.get_async_session() as db:
                result = await self.auth_manager.verify_api_key(db, api_key)
                
                if not result:
                    return None
                
                user, api_key_record = result
                
                # 権限取得
                permissions = await self.auth_manager.get_user_permissions(
                    db, user.id, api_key_record.tenant_id
                )
                
                return {
                    "user": {
                        "id": user.id,
                        "email": user.email
                    },
                    "tenant_id": api_key_record.tenant_id,
                    "permissions": permissions,
                    "auth_type": "api_key"
                }
        
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """レート制限ミドルウェア"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Redis接続（利用可能な場合）
        self.redis_client = None
        self._init_redis()
        
        # インメモリフォールバック
        self.memory_store = defaultdict(lambda: deque())
        
        # レート制限設定
        self.rate_limits = {
            "default": {"requests": 100, "window_seconds": 60},
            "api_key": {"requests": 1000, "window_seconds": 60},
            "public": {"requests": 50, "window_seconds": 60}
        }
    
    def _init_redis(self):
        """Redis初期化（オプション）"""
        try:
            import os
            redis_url = os.getenv("QG_REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
                print("✅ Redis connected for rate limiting")
        except Exception as e:
            print(f"⚠️ Redis not available, using memory store: {e}")
    
    async def dispatch(self, request: Request, call_next):
        # レート制限チェック
        rate_limit_result = await self._check_rate_limit(request)
        
        if not rate_limit_result["allowed"]:
            return Response(
                content=f'{{"detail":"Rate limit exceeded. Try again in {rate_limit_result["retry_after"]} seconds"}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(rate_limit_result["retry_after"])},
                media_type="application/json"
            )
        
        response = await call_next(request)
        
        # レート制限ヘッダー追加
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_result["reset_time"])
        
        return response
    
    async def _check_rate_limit(self, request: Request) -> Dict[str, Any]:
        """レート制限チェック"""
        # クライアント識別
        client_id = self._get_client_id(request)
        
        # レート制限タイプ決定
        limit_type = self._get_limit_type(request)
        config = self.rate_limits[limit_type]
        
        current_time = time.time()
        window_start = current_time - config["window_seconds"]
        
        if self.redis_client:
            return await self._check_rate_limit_redis(
                client_id, config, current_time, window_start
            )
        else:
            return await self._check_rate_limit_memory(
                client_id, config, current_time, window_start
            )
    
    def _get_client_id(self, request: Request) -> str:
        """クライアント識別子取得"""
        # 認証済みユーザー
        if hasattr(request.state, "user"):
            return f"user:{request.state.user['id']}"
        
        # IP Address
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _get_limit_type(self, request: Request) -> str:
        """レート制限タイプ決定"""
        if hasattr(request.state, "user"):
            if request.state.get("auth_type") == "api_key":
                return "api_key"
            else:
                return "default"
        
        # パブリックエンドポイント
        if request.url.path in ["/api/v1/health", "/api/v1/docs"]:
            return "public"
        
        return "default"
    
    async def _check_rate_limit_redis(
        self, 
        client_id: str, 
        config: Dict[str, int], 
        current_time: float, 
        window_start: float
    ) -> Dict[str, Any]:
        """Redis使用レート制限チェック"""
        try:
            key = f"ratelimit:{client_id}"
            
            # スライディングウィンドウカウンター
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.expire(key, config["window_seconds"])
            
            results = await pipe.execute()
            request_count = results[1]
            
            remaining = max(0, config["requests"] - request_count)
            allowed = request_count < config["requests"]
            
            return {
                "allowed": allowed,
                "limit": config["requests"],
                "remaining": remaining,
                "reset_time": int(current_time + config["window_seconds"]),
                "retry_after": config["window_seconds"] if not allowed else 0
            }
            
        except Exception as e:
            print(f"❌ Redis rate limit error: {e}")
            # フォールバック
            return await self._check_rate_limit_memory(client_id, config, current_time, window_start)
    
    async def _check_rate_limit_memory(
        self, 
        client_id: str, 
        config: Dict[str, int], 
        current_time: float, 
        window_start: float
    ) -> Dict[str, Any]:
        """メモリ使用レート制限チェック"""
        requests = self.memory_store[client_id]
        
        # 古いリクエスト削除
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # 新しいリクエスト追加
        requests.append(current_time)
        
        request_count = len(requests)
        remaining = max(0, config["requests"] - request_count)
        allowed = request_count <= config["requests"]
        
        return {
            "allowed": allowed,
            "limit": config["requests"],  
            "remaining": remaining,
            "reset_time": int(current_time + config["window_seconds"]),
            "retry_after": config["window_seconds"] if not allowed else 0
        }


# FastAPI Dependency用のヘルパー関数
async def get_current_user(request: Request) -> Dict[str, Any]:
    """現在のユーザー取得（FastAPI Dependency）"""
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return request.state.user


async def get_current_tenant_id(request: Request) -> str:
    """現在のテナントID取得（FastAPI Dependency）"""
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required"
        )
    
    return request.state.tenant_id


async def get_user_permissions(request: Request) -> List[str]:
    """ユーザー権限取得（FastAPI Dependency）"""
    if not hasattr(request.state, "permissions"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Permission context required"
        )
    
    return request.state.permissions


def require_permission(permission: str):
    """権限チェックDependency"""
    async def check_permission_dependency(
        permissions: List[str] = get_user_permissions
    ):
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permission: {permission}"
            )
        return True
    
    return check_permission_dependency
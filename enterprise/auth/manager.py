#!/usr/bin/env python3
"""
QualityGate Enterprise Authentication Manager
Multi-tenant RBAC + JWT/OAuth2 実装

機能:
- Multi-tenant認証
- Role-based Access Control
- JWT Token管理
- API Key認証
- パフォーマンス制約（50ms以下）
"""

import time
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import and_

from enterprise.database.models import (
    User, Tenant, TenantMembership, Role, Permission, APIKey
)


class AuthenticationManager:
    """認証管理システム"""
    
    def __init__(self):
        # JWT設定
        self.secret_key = self._get_secret_key()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
        # パスワードハッシュ化
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # パフォーマンス制約
        self.auth_processing_max_ms = 50
        
        # 認証統計
        self.auth_stats = {
            "total_authentications": 0,
            "successful_logins": 0,
            "failed_logins": 0,
            "avg_auth_time_ms": 0.0,
            "slow_auths": []
        }
    
    def _get_secret_key(self) -> str:
        """JWT署名キー取得"""
        import os
        secret = os.getenv("QG_JWT_SECRET", "qualitygate-enterprise-secret-key-change-in-production")
        
        if secret == "qualitygate-enterprise-secret-key-change-in-production":
            print("⚠️ WARNING: Using default JWT secret key. Change QG_JWT_SECRET in production!")
        
        return secret
    
    def hash_password(self, password: str) -> str:
        """パスワードハッシュ化"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """パスワード検証"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    async def authenticate_user(
        self, 
        db: Session, 
        email: str, 
        password: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Tuple[User, TenantMembership]]:
        """ユーザー認証"""
        start_time = time.time()
        
        try:
            # ユーザー検索
            user = db.query(User).filter(
                and_(
                    User.email == email,
                    User.is_active == True
                )
            ).first()
            
            if not user:
                self._record_failed_auth(start_time, "user_not_found")
                return None
            
            # パスワード検証
            if not self.verify_password(password, user.hashed_password):
                self._record_failed_auth(start_time, "invalid_password")
                return None
            
            # テナントアクセス権確認
            membership_query = db.query(TenantMembership).filter(
                and_(
                    TenantMembership.user_id == user.id,
                    TenantMembership.is_active == True
                )
            )
            
            if tenant_id:
                membership_query = membership_query.filter(
                    TenantMembership.tenant_id == tenant_id
                )
            
            membership = membership_query.first()
            
            if not membership:
                self._record_failed_auth(start_time, "no_tenant_access")
                return None
            
            # 最終ログイン時刻更新
            user.last_login_at = datetime.now(timezone.utc)
            db.commit()
            
            self._record_successful_auth(start_time)
            return user, membership
            
        except Exception as e:
            self._record_failed_auth(start_time, f"error: {e}")
            raise
    
    def create_access_token(
        self, 
        user: User, 
        membership: TenantMembership,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """アクセストークン作成"""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        # JWT Payload
        payload = {
            "sub": user.id,
            "email": user.email,
            "tenant_id": membership.tenant_id,
            "role_id": membership.role_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """リフレッシュトークン作成"""
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user.id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """トークン検証"""
        start_time = time.time()
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # トークンタイプ確認
            if payload.get("type") != "access":
                return None
            
            # 有効期限確認
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                return None
            
            processing_time = (time.time() - start_time) * 1000
            
            # パフォーマンス制約チェック
            if processing_time > self.auth_processing_max_ms:
                print(f"⚠️ AUTH WARNING: Token verification took {processing_time:.2f}ms (>{self.auth_processing_max_ms}ms limit)")
            
            return payload
            
        except jwt.PyJWTError:
            return None
    
    async def get_user_permissions(
        self, 
        db: Session, 
        user_id: str, 
        tenant_id: str
    ) -> List[str]:
        """ユーザー権限取得"""
        start_time = time.time()
        
        try:
            # テナントメンバーシップとロール取得
            membership = db.query(TenantMembership).filter(
                and_(
                    TenantMembership.user_id == user_id,
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.is_active == True
                )
            ).first()
            
            if not membership:
                return []
            
            # ロールの権限取得
            permissions = db.query(Permission).join(
                Permission.roles
            ).filter(
                Permission.roles.any(role_id=membership.role_id)
            ).all()
            
            permission_names = [f"{p.resource}:{p.action}" for p in permissions]
            
            processing_time = (time.time() - start_time) * 1000
            
            # パフォーマンス制約チェック
            if processing_time > 20:  # 権限取得制約
                print(f"⚠️ AUTH WARNING: Permission lookup took {processing_time:.2f}ms (>20ms limit)")
            
            return permission_names
            
        except Exception as e:
            print(f"❌ Permission lookup error: {e}")
            return []
    
    def generate_api_key(self, user: User, tenant_id: str, name: str) -> Tuple[str, str]:
        """API Key生成"""
        # キープレフィックス（qg_live_, qg_test_）
        prefix = "qg_live_"
        
        # ランダムキー生成（32文字）
        key_suffix = secrets.token_urlsafe(24)[:32]
        full_key = f"{prefix}{key_suffix}"
        
        # ハッシュ化（データベース保存用）
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        return full_key, key_hash
    
    async def verify_api_key(
        self, 
        db: Session, 
        api_key: str
    ) -> Optional[Tuple[User, APIKey]]:
        """API Key検証"""
        start_time = time.time()
        
        try:
            # キー形式確認
            if not api_key.startswith(("qg_live_", "qg_test_")):
                return None
            
            # プレフィックス抽出
            prefix = api_key.split("_", 2)[0] + "_" + api_key.split("_", 2)[1] + "_"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # データベース検索
            api_key_record = db.query(APIKey).filter(
                and_(
                    APIKey.key_prefix == prefix[:10],  # プレフィックス部分のみ
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True
                )
            ).first()
            
            if not api_key_record:
                return None
            
            # 有効期限確認
            if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
                return None
            
            # ユーザー取得
            user = db.query(User).filter(
                and_(
                    User.id == api_key_record.user_id,
                    User.is_active == True
                )
            ).first()
            
            if not user:
                return None
            
            # 最終使用時刻更新
            api_key_record.last_used_at = datetime.now(timezone.utc)
            db.commit()
            
            processing_time = (time.time() - start_time) * 1000
            
            # パフォーマンス制約チェック
            if processing_time > self.auth_processing_max_ms:
                print(f"⚠️ AUTH WARNING: API Key verification took {processing_time:.2f}ms (>{self.auth_processing_max_ms}ms limit)")
            
            return user, api_key_record
            
        except Exception as e:
            print(f"❌ API Key verification error: {e}")
            return None
    
    def _record_successful_auth(self, start_time: float):
        """認証成功記録"""
        processing_time = (time.time() - start_time) * 1000
        
        self.auth_stats["total_authentications"] += 1
        self.auth_stats["successful_logins"] += 1
        
        # 平均時間更新
        total = self.auth_stats["total_authentications"]
        self.auth_stats["avg_auth_time_ms"] = (
            (self.auth_stats["avg_auth_time_ms"] * (total - 1) + processing_time) / total
        )
        
        # 遅い認証記録
        if processing_time > self.auth_processing_max_ms:
            self.auth_stats["slow_auths"].append({
                "duration_ms": processing_time,
                "timestamp": time.time(),
                "type": "successful_login"
            })
            
            # 直近50件のみ保持
            if len(self.auth_stats["slow_auths"]) > 50:
                self.auth_stats["slow_auths"] = self.auth_stats["slow_auths"][-50:]
    
    def _record_failed_auth(self, start_time: float, reason: str):
        """認証失敗記録"""
        processing_time = (time.time() - start_time) * 1000
        
        self.auth_stats["total_authentications"] += 1
        self.auth_stats["failed_logins"] += 1
        
        # 平均時間更新
        total = self.auth_stats["total_authentications"]
        self.auth_stats["avg_auth_time_ms"] = (
            (self.auth_stats["avg_auth_time_ms"] * (total - 1) + processing_time) / total
        )
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """認証統計取得"""
        total = self.auth_stats["total_authentications"]
        if total == 0:
            success_rate = 0.0
        else:
            success_rate = (self.auth_stats["successful_logins"] / total) * 100
        
        return {
            **self.auth_stats,
            "success_rate_pct": success_rate,
            "performance_constraint_ms": self.auth_processing_max_ms
        }


# 権限チェック用ヘルパー関数
async def check_permission(
    auth_manager: AuthenticationManager,
    db: Session,
    user_id: str,
    tenant_id: str,
    required_permission: str
) -> bool:
    """権限チェック"""
    user_permissions = await auth_manager.get_user_permissions(db, user_id, tenant_id)
    return required_permission in user_permissions


def require_permission(permission: str):
    """権限必須デコレータ（FastAPI用）"""
    def decorator(func):
        # FastAPIでの実装は別途必要
        return func
    return decorator
#!/usr/bin/env python3
"""
QualityGate Enterprise Database Models
Multi-tenant Architecture with RBAC Support

テーブル設計:
- Multi-tenant: tenant_id による論理分離
- RBAC: users, roles, permissions, tenant_memberships
- Analytics: metrics, events, aggregated_stats
- Integration: webhooks, external_systems, integration_logs
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, 
    ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# Multi-tenant Base Class
class TenantMixin:
    """Multi-tenant共通機能"""
    tenant_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __init__(self, **kwargs):
        if 'tenant_id' not in kwargs:
            raise ValueError("tenant_id is required for multi-tenant models")
        super().__init__(**kwargs)


# ================ Multi-tenant Management ================

class Tenant(Base):
    """テナント（組織）管理"""
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    settings = Column(JSON, default=dict)
    
    # Subscription & Limits
    plan_type = Column(String(50), default="free")  # free, pro, enterprise
    max_users = Column(Integer, default=5)
    max_api_calls_per_month = Column(Integer, default=1000)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    memberships = relationship("TenantMembership", back_populates="tenant")
    webhooks = relationship("Webhook", back_populates="tenant")
    metrics = relationship("QualityMetric", back_populates="tenant")


# ================ RBAC (Role-Based Access Control) ================

class User(Base):
    """ユーザー管理"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # Profile
    avatar_url = Column(String(500))
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    memberships = relationship("TenantMembership", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")


class Role(Base):
    """ロール定義"""
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Built-in roles: admin, manager, developer, viewer
    is_system_role = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="role")
    memberships = relationship("TenantMembership", back_populates="role")
    
    __table_args__ = (UniqueConstraint('name'),)


class Permission(Base):
    """権限定義"""
    __tablename__ = "permissions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    resource = Column(String(100), nullable=False)  # webhook, analytics, etc.
    action = Column(String(100), nullable=False)    # read, write, delete, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    roles = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    """ロール-権限関連"""
    __tablename__ = "role_permissions"
    
    role_id = Column(String(36), ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(String(36), ForeignKey("permissions.id"), primary_key=True)
    
    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class TenantMembership(Base):
    """テナント-ユーザー-ロール関連"""
    __tablename__ = "tenant_memberships"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
    role = relationship("Role", back_populates="memberships")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id'),
        Index('idx_tenant_user', 'tenant_id', 'user_id'),
    )


# ================ API Management ================

class APIKey(Base):
    """API Key管理"""
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(10), nullable=False)  # qg_live_, qg_test_
    key_hash = Column(String(255), nullable=False)
    
    # Permissions & Limits
    scopes = Column(JSON, default=list)  # ["webhook:read", "analytics:write"]
    rate_limit_per_minute = Column(Integer, default=60)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index('idx_key_prefix_hash', 'key_prefix', 'key_hash'),
    )


# ================ Webhook Management ================

class Webhook(Base, TenantMixin):
    """Webhook設定"""
    __tablename__ = "webhooks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=False)
    secret = Column(String(255))  # HMAC署名用シークレット
    
    # Event Configuration
    events = Column(JSON, default=list)  # ["analysis.completed", "violation.detected"]
    filters = Column(JSON, default=dict)  # 送信条件フィルター
    
    # Settings
    retry_count = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=30)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True))
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="webhooks")
    logs = relationship("WebhookLog", back_populates="webhook")
    
    __table_args__ = (
        Index('idx_tenant_active', 'tenant_id', 'is_active'),
    )


class WebhookLog(Base, TenantMixin):
    """Webhook実行ログ"""
    __tablename__ = "webhook_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    webhook_id = Column(String(36), ForeignKey("webhooks.id"), nullable=False)
    
    # Request/Response
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON)
    response_status = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)
    
    # Timing
    duration_ms = Column(Float)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    webhook = relationship("Webhook", back_populates="logs")
    
    __table_args__ = (
        Index('idx_webhook_triggered', 'webhook_id', 'triggered_at'),
    )


# ================ Analytics & Metrics ================

class QualityMetric(Base, TenantMixin):
    """品質メトリクス"""
    __tablename__ = "quality_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Analysis Data
    analysis_id = Column(String(36), nullable=False)  # 分析セッションID
    input_type = Column(String(50), nullable=False)   # edit, bash, api
    file_type = Column(String(50))
    
    # Results
    violations_critical = Column(Integer, default=0)
    violations_high = Column(Integer, default=0)
    violations_info = Column(Integer, default=0)
    patterns_matched = Column(JSON, default=list)
    
    # Performance
    analysis_time_ms = Column(Float)
    was_blocked = Column(Boolean, default=False)
    bypass_used = Column(Boolean, default=False)
    
    # Context
    project_path = Column(String(500))
    commit_hash = Column(String(40))
    branch_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="metrics")
    
    __table_args__ = (
        Index('idx_tenant_created', 'tenant_id', 'created_at'),
        Index('idx_analysis_id', 'analysis_id'),
    )


class DashboardWidget(Base, TenantMixin):
    """ダッシュボードウィジェット設定"""
    __tablename__ = "dashboard_widgets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    widget_type = Column(String(100), nullable=False)  # violations_chart, performance_trend
    title = Column(String(255), nullable=False)
    config = Column(JSON, default=dict)  # ウィジェット固有設定
    
    # Layout
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=6)
    height = Column(Integer, default=4)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_tenant_user_active', 'tenant_id', 'user_id', 'is_active'),
    )


# ================ External Integrations ================

class ExternalSystem(Base, TenantMixin):
    """外部システム統合設定"""
    __tablename__ = "external_systems"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    system_type = Column(String(100), nullable=False)  # slack, teams, jira, github
    name = Column(String(255), nullable=False)
    
    # Connection Settings
    api_endpoint = Column(String(1000))
    auth_type = Column(String(50))  # oauth2, api_key, webhook
    credentials = Column(JSON)  # 暗号化された認証情報
    
    # Configuration
    settings = Column(JSON, default=dict)
    channel_mappings = Column(JSON, default=dict)  # チャンネル・プロジェクトマッピング
    
    # Status
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True))
    sync_status = Column(String(50), default="pending")  # pending, success, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    integration_logs = relationship("IntegrationLog", back_populates="system")
    
    __table_args__ = (
        Index('idx_tenant_system_type', 'tenant_id', 'system_type'),
    )


class IntegrationLog(Base, TenantMixin):
    """統合実行ログ"""
    __tablename__ = "integration_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    system_id = Column(String(36), ForeignKey("external_systems.id"), nullable=False)
    
    action = Column(String(100), nullable=False)  # send_notification, sync_issues
    payload = Column(JSON)
    response = Column(JSON)
    
    status = Column(String(50), nullable=False)  # success, error, timeout
    error_message = Column(Text)
    duration_ms = Column(Float)
    
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    system = relationship("ExternalSystem", back_populates="integration_logs")
    
    __table_args__ = (
        Index('idx_system_executed', 'system_id', 'executed_at'),
    )


# ================ Database Helper Functions ================

def get_tenant_filter(tenant_id: str, model_class):
    """Multi-tenant用フィルター"""
    if hasattr(model_class, 'tenant_id'):
        return model_class.tenant_id == tenant_id
    else:
        raise ValueError(f"Model {model_class.__name__} does not support multi-tenancy")


def create_sample_data(db: Session, tenant_id: str):
    """サンプルデータ作成（開発・テスト用）"""
    
    # Sample Tenant
    tenant = Tenant(
        id=tenant_id,
        name="Sample Organization",
        slug="sample-org",
        description="Sample tenant for testing",
        plan_type="pro"
    )
    db.add(tenant)
    
    # Sample Roles
    admin_role = Role(name="admin", description="Full administrative access", is_system_role=True)
    dev_role = Role(name="developer", description="Development team access", is_system_role=True)
    viewer_role = Role(name="viewer", description="Read-only access", is_system_role=True)
    
    db.add_all([admin_role, dev_role, viewer_role])
    
    # Sample Permissions
    permissions = [
        Permission(name="webhook:read", resource="webhook", action="read"),
        Permission(name="webhook:write", resource="webhook", action="write"),
        Permission(name="analytics:read", resource="analytics", action="read"),
        Permission(name="analytics:write", resource="analytics", action="write"),
        Permission(name="tenant:admin", resource="tenant", action="admin"),
    ]
    db.add_all(permissions)
    
    db.commit()
    print(f"✅ Sample data created for tenant: {tenant_id}")
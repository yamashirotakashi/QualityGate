#!/usr/bin/env python3
"""
QualityGate Enterprise Database Connection Manager
SQLite (開発) + PostgreSQL (本番) 対応
"""

import os
import time
import asyncio
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from enterprise.database.models import Base, create_sample_data


# 追加のSQLAlchemy import (セキュリティ修正用)
from sqlalchemy.sql import func, select

class DatabaseManager:
    """データベース接続管理"""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.async_database_url = self._get_async_database_url()
        
        # Engines
        self.engine = None
        self.async_engine = None
        
        # Session Makers
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        
        # Connection State
        self._is_connected = False
        self._initialization_time = None
        
    def _get_database_url(self) -> str:
        """データベースURL取得"""
        # 環境変数から設定取得
        db_type = os.getenv("QG_DATABASE_TYPE", "sqlite")
        
        if db_type == "postgresql":
            # PostgreSQL (本番環境)
            db_user = os.getenv("QG_DATABASE_USER", "qualitygate")
            db_password = os.getenv("QG_DATABASE_PASSWORD", "")
            db_host = os.getenv("QG_DATABASE_HOST", "localhost")
            db_port = os.getenv("QG_DATABASE_PORT", "5432")
            db_name = os.getenv("QG_DATABASE_NAME", "qualitygate_enterprise")
            
            return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
        else:
            # SQLite (開発・テスト環境)
            db_path = os.getenv("QG_DATABASE_PATH", "/mnt/c/Users/tky99/dev/qualitygate/enterprise/qualitygate.db")
            return f"sqlite:///{db_path}"
    
    def _get_async_database_url(self) -> str:
        """非同期データベースURL取得"""
        sync_url = self.database_url
        
        if sync_url.startswith("postgresql://"):
            return sync_url.replace("postgresql://", "postgresql+asyncpg://")
        elif sync_url.startswith("sqlite:///"):
            return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        else:
            return sync_url
    
    async def initialize(self):
        """データベース初期化"""
        start_time = time.time()
        
        try:
            # 非同期エンジン作成
            if self.database_url.startswith("sqlite"):
                # SQLite設定
                self.async_engine = create_async_engine(
                    self.async_database_url,
                    echo=False,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 20
                    }
                )
                
                # 同期エンジン（マイグレーション用）
                self.engine = create_engine(
                    self.database_url,
                    echo=False,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False}
                )
                
            else:
                # PostgreSQL設定
                self.async_engine = create_async_engine(
                    self.async_database_url,
                    echo=False,
                    pool_size=20,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=3600
                )
                
                self.engine = create_engine(
                    self.database_url,
                    echo=False,
                    pool_size=20,
                    max_overflow=10
                )
            
            # セッションファクトリー作成
            self.AsyncSessionLocal = async_sessionmaker(
                self.async_engine, 
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            # データベーステーブル作成
            await self._create_tables()
            
            # 接続テスト
            await self._test_connection()
            
            self._is_connected = True
            self._initialization_time = (time.time() - start_time) * 1000
            
            print(f"✅ Database initialized in {self._initialization_time:.2f}ms")
            print(f"📊 Database type: {self.database_url.split('://')[0]}")
            
            # パフォーマンス制約チェック
            if self._initialization_time > 100:  # DB初期化制約
                print(f"⚠️ WARNING: Database initialization took {self._initialization_time:.2f}ms (>100ms limit)")
                
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise
    
    async def _create_tables(self):
        """テーブル作成"""
        try:
            # 非同期でテーブル作成
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            print("✅ Database tables created/verified")
            
        except Exception as e:
            print(f"❌ Table creation failed: {e}")
            raise
    
    async def _test_connection(self):
        """接続テスト"""
        try:
            async with self.AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                if test_value != 1:
                    raise Exception("Connection test failed")
                
            print("✅ Database connection test passed")
            
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            raise
    
    def is_connected(self) -> bool:
        """接続状態確認"""
        return self._is_connected
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """非同期セッション取得"""
        if not self._is_connected:
            raise Exception("Database not initialized")
        
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    def get_sync_session(self) -> Session:
        """同期セッション取得（マイグレーション・初期化用）"""
        if not self.SessionLocal:
            raise Exception("Database not initialized")
        
        return self.SessionLocal()
    
    async def create_sample_tenant(self, tenant_id: str = "sample-tenant-001"):
        """サンプルテナント作成（開発用）"""
        try:
            # 同期セッションでサンプルデータ作成
            with self.get_sync_session() as session:
                create_sample_data(session, tenant_id)
            
            print(f"✅ Sample tenant created: {tenant_id}")
            return tenant_id
            
        except Exception as e:
            print(f"❌ Sample tenant creation failed: {e}")
            raise
    
    async def get_database_stats(self):
        """データベース統計情報取得"""
        if not self._is_connected:
            return {"status": "not_connected"}
        
        try:
            stats = {
                "status": "connected",
                "type": self.database_url.split("://")[0],
                "initialization_time_ms": self._initialization_time,
                "tables": []
            }
            
            # セキュリティ修正: テーブル名の許可リストによる検証
            allowed_tables = {
                "tenants": "tenants",
                "users": "users", 
                "webhooks": "webhooks",
                "quality_metrics": "quality_metrics"
            }
            
            # テーブル統計（安全な実装）
            async with self.AsyncSessionLocal() as session:
                for table_key in allowed_tables.keys():
                    table_name = allowed_tables[table_key]  # 許可されたテーブル名のみ使用
                    try:
                        # SQLAlchemy のメタデータから安全にテーブル参照
                        if hasattr(Base.metadata.tables, table_name):
                            table_obj = Base.metadata.tables[table_name]
                            result = await session.execute(select(func.count()).select_from(table_obj))
                            count = result.scalar()
                            stats["tables"].append({"name": table_name, "count": count})
                        else:
                            # テーブルが存在しない場合の安全な処理
                            stats["tables"].append({"name": table_name, "count": "N/A"})
                    except Exception:
                        stats["tables"].append({"name": table_name, "count": "N/A"})
            
            return stats
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def close(self):
        """データベース接続クローズ"""
        try:
            if self.async_engine:
                await self.async_engine.dispose()
            
            if self.engine:
                self.engine.dispose()
            
            self._is_connected = False
            print("✅ Database connections closed")
            
        except Exception as e:
            print(f"❌ Database close error: {e}")


# Dependency Injection用のヘルパー関数
async def get_database() -> AsyncSession:
    """FastAPI Dependency: データベースセッション取得"""
    # これはFastAPIアプリケーションで使用される
    # 実際の実装はmain.pyで設定される
    pass


# Performance Monitoring
class DatabasePerformanceMonitor:
    """データベースパフォーマンス監視"""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_queries = []
        self.total_queries = 0
        self.avg_query_time = 0.0
    
    async def record_query(self, query: str, duration_ms: float):
        """クエリ実行時間記録"""
        self.total_queries += 1
        
        # 平均実行時間更新
        self.avg_query_time = (
            (self.avg_query_time * (self.total_queries - 1) + duration_ms) / 
            self.total_queries
        )
        
        # 遅いクエリ記録（30ms制約）
        if duration_ms > 30:
            self.slow_queries.append({
                "query": query[:200],  # クエリ内容（最初の200文字）
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })
            
            # 直近100件のみ保持
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]
    
    def get_stats(self):
        """統計情報取得"""
        return {
            "total_queries": self.total_queries,
            "avg_query_time_ms": self.avg_query_time,
            "slow_queries_count": len(self.slow_queries),
            "recent_slow_queries": self.slow_queries[-10:] if self.slow_queries else []
        }
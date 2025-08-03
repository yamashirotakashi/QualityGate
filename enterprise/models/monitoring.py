#!/usr/bin/env python3
"""
QualityGate Enterprise Performance Monitor
Real-time performance tracking and constraint validation
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum


class MetricType(Enum):
    """メトリクスタイプ"""
    API_RESPONSE_TIME = "api_response_time"
    AUTH_PROCESSING_TIME = "auth_processing_time"  
    DB_QUERY_TIME = "db_query_time"
    CORE_ANALYSIS_TIME = "core_analysis_time"
    SECURITY_VALIDATION_TIME = "security_validation_time"
    INTEGRATION_RESPONSE_TIME = "integration_response_time"


@dataclass
class PerformanceMetric:
    """パフォーマンスメトリクス"""
    metric_type: MetricType
    value: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: Optional[str] = None


@dataclass
class ConstraintViolation:
    """制約違反"""
    metric_type: MetricType
    value: float
    constraint: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    severity: str = "WARNING"


class PerformanceMonitor:
    """パフォーマンス監視システム"""
    
    def __init__(self):
        # パフォーマンス制約定義
        self.constraints = {
            MetricType.API_RESPONSE_TIME: 100.0,         # API応答時間: 100ms以下
            MetricType.AUTH_PROCESSING_TIME: 50.0,       # 認証処理: 50ms以下
            MetricType.DB_QUERY_TIME: 30.0,              # データベースクエリ: 30ms以下
            MetricType.CORE_ANALYSIS_TIME: 1.5,          # Core分析: 1.5ms以下
            MetricType.SECURITY_VALIDATION_TIME: 10.0,   # セキュリティ検証: 10ms以下
            MetricType.INTEGRATION_RESPONSE_TIME: 5000.0 # 外部統合: 5秒以下
        }
        
        # メトリクス履歴（最新1000件）
        self.metrics_history: Dict[MetricType, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 制約違反履歴（最新500件）
        self.violation_history: deque = deque(maxlen=500)
        
        # リアルタイム統計
        self.realtime_stats: Dict[MetricType, Dict[str, float]] = defaultdict(dict)
        
        # テナント別統計
        self.tenant_stats: Dict[str, Dict[MetricType, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        
        # アラート設定
        self.alert_thresholds = {
            "violation_rate_pct": 5.0,      # 制約違反率5%でアラート
            "avg_response_degradation": 2.0, # 平均応答時間が2倍になったらアラート
            "consecutive_violations": 5      # 連続5回違反でアラート
        }
        
        # 統計
        self.monitor_stats = {
            "total_metrics": 0,
            "total_violations": 0,
            "active_tenants": set(),
            "monitoring_uptime": time.time()
        }
        
        # 連続違反カウンター
        self.consecutive_violations: Dict[MetricType, int] = defaultdict(int)
    
    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ):
        """メトリクス記録"""
        timestamp = time.time()
        
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=timestamp,
            metadata=metadata or {},
            tenant_id=tenant_id
        )
        
        # 履歴に追加
        self.metrics_history[metric_type].append(metric)
        
        # 統計更新
        self.monitor_stats["total_metrics"] += 1
        if tenant_id:
            self.monitor_stats["active_tenants"].add(tenant_id)
        
        # リアルタイム統計更新
        await self._update_realtime_stats(metric_type, value)
        
        # テナント別統計更新
        if tenant_id:
            await self._update_tenant_stats(tenant_id, metric_type, value)
        
        # 制約チェック
        await self._check_constraints(metric)
    
    async def record_request(
        self,
        path: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        tenant_id: Optional[str] = None
    ):
        """HTTPリクエスト記録"""
        metadata = {
            "path": path,
            "method": method,
            "status_code": status_code
        }
        
        await self.record_metric(
            MetricType.API_RESPONSE_TIME,
            response_time_ms,
            metadata,
            tenant_id
        )
    
    async def record_auth_operation(
        self,
        operation: str,
        processing_time_ms: float,
        success: bool,
        tenant_id: Optional[str] = None
    ):
        """認証操作記録"""
        metadata = {
            "operation": operation,
            "success": success
        }
        
        await self.record_metric(
            MetricType.AUTH_PROCESSING_TIME,
            processing_time_ms,
            metadata,
            tenant_id
        )
    
    async def record_db_query(
        self,
        query_type: str,
        execution_time_ms: float,
        rows_affected: int = 0,
        tenant_id: Optional[str] = None
    ):
        """データベースクエリ記録"""
        metadata = {
            "query_type": query_type,
            "rows_affected": rows_affected
        }
        
        await self.record_metric(
            MetricType.DB_QUERY_TIME,
            execution_time_ms,
            metadata,
            tenant_id
        )
    
    async def record_core_analysis(
        self,
        analysis_time_ms: float,
        patterns_checked: int,
        violations_found: int,
        tenant_id: Optional[str] = None
    ):
        """Core分析記録"""
        metadata = {
            "patterns_checked": patterns_checked,
            "violations_found": violations_found
        }
        
        await self.record_metric(
            MetricType.CORE_ANALYSIS_TIME,
            analysis_time_ms,
            metadata,
            tenant_id
        )
    
    async def record_integration_call(
        self,
        integration_type: str,
        response_time_ms: float,
        success: bool,
        tenant_id: Optional[str] = None
    ):
        """外部統合呼び出し記録"""
        metadata = {
            "integration_type": integration_type,
            "success": success
        }
        
        await self.record_metric(
            MetricType.INTEGRATION_RESPONSE_TIME,
            response_time_ms,
            metadata,
            tenant_id
        )
    
    async def _update_realtime_stats(self, metric_type: MetricType, value: float):
        """リアルタイム統計更新"""
        stats = self.realtime_stats[metric_type]
        
        # 初期化
        if not stats:
            stats.update({
                "count": 0,
                "sum": 0.0,
                "min": float('inf'),
                "max": float('-inf'),
                "avg": 0.0
            })
        
        # 統計更新
        stats["count"] += 1
        stats["sum"] += value
        stats["min"] = min(stats["min"], value)
        stats["max"] = max(stats["max"], value)
        stats["avg"] = stats["sum"] / stats["count"]
        
        # 直近100件の統計も計算
        recent_metrics = list(self.metrics_history[metric_type])[-100:]
        if recent_metrics:
            recent_values = [m.value for m in recent_metrics]
            stats["recent_avg"] = sum(recent_values) / len(recent_values)
            stats["recent_count"] = len(recent_values)
    
    async def _update_tenant_stats(self, tenant_id: str, metric_type: MetricType, value: float):
        """テナント別統計更新"""
        stats = self.tenant_stats[tenant_id][metric_type]
        
        # 初期化
        if not stats:
            stats.update({
                "count": 0,
                "sum": 0.0,
                "avg": 0.0
            })
        
        # 統計更新
        stats["count"] += 1
        stats["sum"] += value
        stats["avg"] = stats["sum"] / stats["count"]
    
    async def _check_constraints(self, metric: PerformanceMetric):
        """制約チェック"""
        constraint = self.constraints.get(metric.metric_type)
        
        if constraint and metric.value > constraint:
            # 制約違反
            violation = ConstraintViolation(
                metric_type=metric.metric_type,
                value=metric.value,
                constraint=constraint,
                timestamp=metric.timestamp,
                metadata=metric.metadata,
                severity=self._determine_violation_severity(metric.metric_type, metric.value, constraint)
            )
            
            self.violation_history.append(violation)
            self.monitor_stats["total_violations"] += 1
            
            # 連続違反カウント
            self.consecutive_violations[metric.metric_type] += 1
            
            # アラートチェック
            await self._check_alerts(violation)
            
            print(f"⚠️ PERFORMANCE VIOLATION: {metric.metric_type.value} = {metric.value:.2f} (limit: {constraint})")
            
        else:
            # 制約内の場合、連続違反カウンターリセット
            self.consecutive_violations[metric.metric_type] = 0
    
    def _determine_violation_severity(self, metric_type: MetricType, value: float, constraint: float) -> str:
        """制約違反の重要度判定"""
        ratio = value / constraint
        
        if ratio >= 5.0:
            return "CRITICAL"
        elif ratio >= 3.0:
            return "HIGH"
        elif ratio >= 2.0:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _check_alerts(self, violation: ConstraintViolation):
        """アラートチェック"""
        # 連続違反アラート
        consecutive_count = self.consecutive_violations[violation.metric_type]
        if consecutive_count >= self.alert_thresholds["consecutive_violations"]:
            print(f"🚨 ALERT: {consecutive_count} consecutive violations for {violation.metric_type.value}")
            
            # アラート送信処理（Integration Busと連携）
            # await self._send_performance_alert(violation)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンス概要取得"""
        summary = {
            "monitoring_uptime_seconds": time.time() - self.monitor_stats["monitoring_uptime"],
            "total_metrics": self.monitor_stats["total_metrics"],
            "total_violations": self.monitor_stats["total_violations"],
            "active_tenants": len(self.monitor_stats["active_tenants"]),
            "violation_rate_pct": 0.0
        }
        
        # 違反率計算
        if self.monitor_stats["total_metrics"] > 0:
            summary["violation_rate_pct"] = (
                self.monitor_stats["total_violations"] / self.monitor_stats["total_metrics"]
            ) * 100
        
        # メトリクス別統計
        summary["metrics"] = {}
        for metric_type, stats in self.realtime_stats.items():
            summary["metrics"][metric_type.value] = {
                "count": stats.get("count", 0),
                "avg": stats.get("avg", 0.0),
                "recent_avg": stats.get("recent_avg", 0.0),
                "constraint": self.constraints.get(metric_type, 0.0),
                "constraint_violations": sum(
                    1 for v in self.violation_history 
                    if v.metric_type == metric_type
                ),
                "consecutive_violations": self.consecutive_violations[metric_type]
            }
        
        return summary
    
    def get_tenant_performance(self, tenant_id: str) -> Dict[str, Any]:
        """テナント別パフォーマンス取得"""
        if tenant_id not in self.tenant_stats:
            return {"error": "Tenant not found"}
        
        tenant_data = {
            "tenant_id": tenant_id,
            "metrics": {}
        }
        
        for metric_type, stats in self.tenant_stats[tenant_id].items():
            tenant_data["metrics"][metric_type.value] = {
                "count": stats.get("count", 0),
                "avg": stats.get("avg", 0.0),
                "constraint": self.constraints.get(metric_type, 0.0)
            }
        
        return tenant_data
    
    def get_recent_violations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """最近の制約違反取得"""
        recent_violations = list(self.violation_history)[-limit:]
        
        return [
            {
                "metric_type": v.metric_type.value,
                "value": v.value,
                "constraint": v.constraint,
                "timestamp": v.timestamp,
                "severity": v.severity,
                "metadata": v.metadata
            }
            for v in recent_violations
        ]
    
    def get_constraint_compliance(self) -> Dict[str, float]:
        """制約準拠率取得"""
        compliance = {}
        
        for metric_type in MetricType:
            if metric_type in self.realtime_stats:
                stats = self.realtime_stats[metric_type]
                violations = sum(
                    1 for v in self.violation_history 
                    if v.metric_type == metric_type
                )
                
                total_count = stats.get("count", 0)
                if total_count > 0:
                    compliance_rate = ((total_count - violations) / total_count) * 100
                    compliance[metric_type.value] = compliance_rate
                else:
                    compliance[metric_type.value] = 100.0
        
        return compliance
    
    async def reset_stats(self):
        """統計リセット"""
        self.metrics_history.clear()
        self.violation_history.clear()
        self.realtime_stats.clear()
        self.tenant_stats.clear()
        self.consecutive_violations.clear()
        
        self.monitor_stats = {
            "total_metrics": 0,
            "total_violations": 0,
            "active_tenants": set(),
            "monitoring_uptime": time.time()
        }
        
        print("✅ Performance monitoring stats reset")


# 使用例とテスト
async def test_performance_monitor():
    """パフォーマンス監視テスト"""
    
    monitor = PerformanceMonitor()
    
    # テストメトリクス記録
    print("🧪 Testing performance monitoring...")
    
    # API応答時間（正常）
    await monitor.record_request("/api/v1/webhooks", "GET", 45.0, 200, "tenant-001")
    
    # API応答時間（制約違反）
    await monitor.record_request("/api/v1/analytics", "POST", 150.0, 200, "tenant-001")
    
    # 認証処理時間（正常）
    await monitor.record_auth_operation("jwt_verify", 25.0, True, "tenant-001")
    
    # データベースクエリ（制約違反）
    await monitor.record_db_query("SELECT", 45.0, 100, "tenant-001")
    
    # Core分析時間（正常）
    await monitor.record_core_analysis(0.8, 50, 2, "tenant-001")
    
    # 外部統合呼び出し（制約違反）
    await monitor.record_integration_call("slack", 6000.0, True, "tenant-001")
    
    # 概要表示
    summary = monitor.get_performance_summary()
    print("📊 Performance Summary:")
    for key, value in summary.items():
        if key != "metrics":
            print(f"  {key}: {value}")
    
    print("\n📈 Metrics Details:")
    for metric_name, stats in summary["metrics"].items():
        print(f"  {metric_name}: avg={stats['avg']:.2f}ms, violations={stats['constraint_violations']}")
    
    # 制約準拠率
    compliance = monitor.get_constraint_compliance()
    print(f"\n✅ Constraint Compliance: {compliance}")
    
    # 最近の違反
    violations = monitor.get_recent_violations(10)
    print(f"\n⚠️ Recent Violations: {len(violations)} found")
    for violation in violations:
        print(f"  {violation['metric_type']}: {violation['value']:.2f} > {violation['constraint']} ({violation['severity']})")


if __name__ == "__main__":
    asyncio.run(test_performance_monitor())
#!/usr/bin/env python3
"""
QualityGate Integration Bus
Centralized external system integration management
"""

import time
import asyncio
import json
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
from enum import Enum

from enterprise.integrations.slack import SlackIntegration
from enterprise.integrations.jira import JIRAIntegration


class IntegrationType(Enum):
    """統合タイプ"""
    SLACK = "slack"
    JIRA = "jira"
    TEAMS = "teams"
    GITHUB = "github"
    WEBHOOK = "webhook"


@dataclass
class IntegrationConfig:
    """統合設定"""
    integration_type: IntegrationType
    name: str
    enabled: bool
    config: Dict[str, Any]
    tenant_id: str
    created_at: float
    last_used: Optional[float] = None


@dataclass
class NotificationEvent:
    """通知イベント"""
    event_type: str
    data: Dict[str, Any]
    tenant_id: str
    severity: str
    timestamp: float


class IntegrationBus:
    """統合バス管理システム"""
    
    def __init__(self):
        # アクティブな統合
        self.integrations: Dict[str, Any] = {}
        
        # 統合設定
        self.integration_configs: Dict[str, IntegrationConfig] = {}
        
        # イベントキュー
        self.event_queue: List[NotificationEvent] = []
        
        # パフォーマンス制約
        self.max_processing_time_ms = 1000  # 1秒以内
        self.max_queue_size = 1000
        
        # 統計
        self.bus_stats = {
            "total_events": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "active_integrations": 0,
            "avg_processing_time_ms": 0.0,
            "queue_size": 0
        }
        
        # 処理中フラグ
        self._processing = False
    
    async def register_integration(
        self, 
        integration_id: str,
        integration_type: IntegrationType,
        name: str,
        config: Dict[str, Any],
        tenant_id: str
    ) -> bool:
        """統合登録"""
        try:
            # 統合設定保存
            integration_config = IntegrationConfig(
                integration_type=integration_type,
                name=name,
                enabled=True,
                config=config,
                tenant_id=tenant_id,
                created_at=time.time()
            )
            
            self.integration_configs[integration_id] = integration_config
            
            # 統合インスタンス作成
            integration_instance = await self._create_integration_instance(
                integration_type, config
            )
            
            if integration_instance:
                self.integrations[integration_id] = integration_instance
                self.bus_stats["active_integrations"] = len(self.integrations)
                
                print(f"✅ Integration registered: {integration_id} ({integration_type.value})")
                return True
            else:
                print(f"❌ Failed to create integration instance: {integration_id}")
                return False
                
        except Exception as e:
            print(f"❌ Integration registration failed: {e}")
            return False
    
    async def unregister_integration(self, integration_id: str) -> bool:
        """統合解除"""
        try:
            if integration_id in self.integrations:
                del self.integrations[integration_id]
            
            if integration_id in self.integration_configs:
                del self.integration_configs[integration_id]
            
            self.bus_stats["active_integrations"] = len(self.integrations)
            
            print(f"✅ Integration unregistered: {integration_id}")
            return True
            
        except Exception as e:
            print(f"❌ Integration unregistration failed: {e}")
            return False
    
    async def send_notification(
        self,
        event_type: str,
        data: Dict[str, Any],
        tenant_id: str,
        severity: str = "INFO",
        target_integrations: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """通知送信"""
        start_time = time.time()
        
        try:
            # イベント作成
            event = NotificationEvent(
                event_type=event_type,
                data=data,
                tenant_id=tenant_id,
                severity=severity,
                timestamp=time.time()
            )
            
            # キューサイズチェック
            if len(self.event_queue) >= self.max_queue_size:
                print(f"⚠️ Event queue is full, dropping oldest events")
                self.event_queue = self.event_queue[-self.max_queue_size//2:]
            
            self.event_queue.append(event)
            self.bus_stats["total_events"] += 1
            self.bus_stats["queue_size"] = len(self.event_queue)
            
            # 通知処理
            results = await self._process_notification(event, target_integrations)
            
            processing_time = (time.time() - start_time) * 1000
            
            # 統計更新
            successful = sum(1 for success in results.values() if success)
            failed = len(results) - successful
            
            self.bus_stats["successful_deliveries"] += successful
            self.bus_stats["failed_deliveries"] += failed
            
            # 平均処理時間更新
            total = self.bus_stats["total_events"]
            self.bus_stats["avg_processing_time_ms"] = (
                (self.bus_stats["avg_processing_time_ms"] * (total - 1) + processing_time) / total
            )
            
            # パフォーマンス制約チェック
            if processing_time > self.max_processing_time_ms:
                print(f"⚠️ BUS WARNING: Notification processing took {processing_time:.2f}ms (>{self.max_processing_time_ms}ms limit)")
            
            return results
            
        except Exception as e:
            print(f"❌ Notification sending failed: {e}")
            return {}
    
    async def send_quality_violation_alert(
        self,
        violation_data: Dict[str, Any],
        tenant_id: str
    ) -> Dict[str, bool]:
        """品質違反アラート送信"""
        return await self.send_notification(
            event_type="quality.violation",
            data=violation_data,
            tenant_id=tenant_id,
            severity=violation_data.get("severity", "INFO")
        )
    
    async def send_daily_report(
        self,
        analytics_data: Dict[str, Any],
        tenant_id: str
    ) -> Dict[str, bool]:
        """日次レポート送信"""
        return await self.send_notification(
            event_type="analytics.daily_report",
            data=analytics_data,
            tenant_id=tenant_id,
            severity="INFO"
        )
    
    async def send_system_alert(
        self,
        alert_message: str,
        tenant_id: str,
        severity: str = "HIGH",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """システムアラート送信"""
        data = {
            "message": alert_message,
            "metadata": metadata or {}
        }
        
        return await self.send_notification(
            event_type="system.alert",
            data=data,
            tenant_id=tenant_id,
            severity=severity
        )
    
    async def _process_notification(
        self,
        event: NotificationEvent,
        target_integrations: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """通知処理（内部）"""
        results = {}
        
        # 対象統合決定
        if target_integrations:
            integrations_to_process = {
                k: v for k, v in self.integrations.items() 
                if k in target_integrations
            }
        else:
            # テナント別フィルタリング
            integrations_to_process = {
                k: v for k, v in self.integrations.items()
                if self.integration_configs[k].tenant_id == event.tenant_id and
                   self.integration_configs[k].enabled
            }
        
        # 並行処理で通知送信
        tasks = []
        for integration_id, integration in integrations_to_process.items():
            task = self._send_to_integration(integration_id, integration, event)
            tasks.append((integration_id, task))
        
        # すべての通知を並行実行
        for integration_id, task in tasks:
            try:
                success = await task
                results[integration_id] = success
                
                # 最終使用時刻更新
                if integration_id in self.integration_configs:
                    self.integration_configs[integration_id].last_used = time.time()
                    
            except Exception as e:
                print(f"❌ Integration {integration_id} failed: {e}")
                results[integration_id] = False
        
        return results
    
    async def _send_to_integration(
        self,
        integration_id: str,
        integration: Any,
        event: NotificationEvent
    ) -> bool:
        """個別統合への送信"""
        try:
            config = self.integration_configs[integration_id]
            
            if config.integration_type == IntegrationType.SLACK:
                return await self._send_to_slack(integration, event)
            elif config.integration_type == IntegrationType.JIRA:
                return await self._send_to_jira(integration, event)
            elif config.integration_type == IntegrationType.WEBHOOK:
                return await self._send_to_webhook(integration, event, config.config)
            else:
                print(f"⚠️ Unsupported integration type: {config.integration_type}")
                return False
                
        except Exception as e:
            print(f"❌ Send to integration {integration_id} failed: {e}")
            return False
    
    async def _send_to_slack(self, slack: SlackIntegration, event: NotificationEvent) -> bool:
        """Slackへの送信"""
        if event.event_type == "quality.violation":
            channel = "#quality-alerts"
            return await slack.send_violation_alert(event.data, channel)
        elif event.event_type == "analytics.daily_report":
            channel = "#quality-reports"
            return await slack.send_daily_report(event.data, channel)
        elif event.event_type == "system.alert":
            channel = "#system-alerts"
            return await slack.send_custom_notification(
                event.data["message"],
                channel,
                event.severity,
                event.data.get("metadata")
            )
        else:
            # カスタム通知
            channel = "#general"
            return await slack.send_custom_notification(
                f"Event: {event.event_type}",
                channel,
                event.severity,
                event.data
            )
    
    async def _send_to_jira(self, jira: JIRAIntegration, event: NotificationEvent) -> bool:
        """JIRAへの送信"""
        if event.event_type == "quality.violation":
            issue_key = await jira.create_violation_issue(event.data)
            return issue_key is not None
        else:
            # その他のイベントは対応しない
            return True
    
    async def _send_to_webhook(
        self,
        webhook_url: str,
        event: NotificationEvent,
        config: Dict[str, Any]
    ) -> bool:
        """Webhookへの送信"""
        try:
            import httpx
            
            payload = {
                "event_type": event.event_type,
                "data": event.data,
                "tenant_id": event.tenant_id,
                "severity": event.severity,
                "timestamp": event.timestamp
            }
            
            headers = config.get("headers", {})
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Webhook send error: {e}")
            return False
    
    async def _create_integration_instance(
        self,
        integration_type: IntegrationType,
        config: Dict[str, Any]
    ) -> Optional[Any]:
        """統合インスタンス作成"""
        try:
            if integration_type == IntegrationType.SLACK:
                webhook_url = config.get("webhook_url")
                bot_token = config.get("bot_token")
                if webhook_url:
                    return SlackIntegration(webhook_url, bot_token)
                    
            elif integration_type == IntegrationType.JIRA:
                base_url = config.get("base_url")
                username = config.get("username")
                api_token = config.get("api_token")
                project = config.get("default_project")
                
                if all([base_url, username, api_token, project]):
                    return JIRAIntegration(base_url, username, api_token, project)
                    
            elif integration_type == IntegrationType.WEBHOOK:
                webhook_url = config.get("url")
                if webhook_url:
                    return webhook_url
            
            else:
                print(f"⚠️ Unsupported integration type: {integration_type}")
                
        except Exception as e:
            print(f"❌ Integration instance creation failed: {e}")
        
        return None
    
    def get_integration_status(self) -> Dict[str, Any]:
        """統合ステータス取得"""
        integrations_status = {}
        
        for integration_id, config in self.integration_configs.items():
            integrations_status[integration_id] = {
                "type": config.integration_type.value,
                "name": config.name,
                "enabled": config.enabled,
                "tenant_id": config.tenant_id,
                "created_at": config.created_at,
                "last_used": config.last_used,
                "active": integration_id in self.integrations
            }
        
        return {
            "integrations": integrations_status,
            "statistics": self.bus_stats,
            "queue_size": len(self.event_queue),
            "performance_constraint_ms": self.max_processing_time_ms
        }
    
    async def process_event_queue(self):
        """イベントキュー処理（バックグラウンド）"""
        if self._processing:
            return
        
        self._processing = True
        
        try:
            while self.event_queue:
                event = self.event_queue.pop(0)
                await self._process_notification(event)
                
                # キューサイズ更新
                self.bus_stats["queue_size"] = len(self.event_queue)
                
                # 少し待機（CPU負荷軽減）
                await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"❌ Event queue processing error: {e}")
        finally:
            self._processing = False


# 使用例とテスト
async def test_integration_bus():
    """統合バステスト"""
    
    bus = IntegrationBus()
    
    # Slack統合登録
    slack_config = {
        "webhook_url": "https://hooks.slack.com/services/TEST/TEST/TEST"
    }
    
    await bus.register_integration(
        "slack-main",
        IntegrationType.SLACK,
        "Main Slack Channel",
        slack_config,
        "sample-tenant-001"
    )
    
    # JIRA統合登録
    jira_config = {
        "base_url": "https://test.atlassian.net",
        "username": "test@example.com",
        "api_token": "test-token",
        "default_project": "QG"
    }
    
    await bus.register_integration(
        "jira-main",
        IntegrationType.JIRA,
        "Main JIRA Project",
        jira_config,
        "sample-tenant-001"
    )
    
    # 品質違反アラートテスト
    violation_data = {
        "severity": "CRITICAL",
        "pattern": "Hardcoded API Key",
        "file_path": "config/api.py",
        "message": "API_KEY = 'abc123' detected",
        "blocked": True
    }
    
    print("🧪 Testing quality violation alert...")
    results = await bus.send_quality_violation_alert(
        violation_data,
        "sample-tenant-001"
    )
    print(f"Results: {results}")
    
    # システムアラートテスト
    print("🧪 Testing system alert...")
    results = await bus.send_system_alert(
        "High memory usage detected",
        "sample-tenant-001",
        "HIGH",
        {"memory_usage": "95%", "service": "qualitygate-api"}
    )
    print(f"Results: {results}")
    
    # ステータス確認
    status = bus.get_integration_status()
    print(f"📊 Integration Bus Status: {json.dumps(status, indent=2, default=str)}")


if __name__ == "__main__":
    asyncio.run(test_integration_bus())
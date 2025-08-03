#!/usr/bin/env python3
"""
QualityGate Slack Integration
Quality violation notifications and reporting
"""

import time
import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import httpx
from fastapi import HTTPException


@dataclass
class SlackMessage:
    """Slack メッセージ構造"""
    channel: str
    text: str
    blocks: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    thread_ts: Optional[str] = None


class SlackIntegration:
    """Slack統合クライアント"""
    
    def __init__(self, webhook_url: str, bot_token: Optional[str] = None):
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.base_url = "https://slack.com/api"
        
        # パフォーマンス制約
        self.max_response_time_ms = 5000  # 5秒以内
        
        # 統計
        self.integration_stats = {
            "messages_sent": 0,
            "failed_sends": 0,
            "avg_response_time_ms": 0.0
        }
    
    async def send_violation_alert(
        self, 
        violation_data: Dict[str, Any],
        channel: str = "#quality-alerts"
    ) -> bool:
        """品質違反アラート送信"""
        start_time = time.time()
        
        try:
            # 重要度による色分け
            color_map = {
                "CRITICAL": "#ff0000",  # 赤
                "HIGH": "#ff9900",      # オレンジ  
                "INFO": "#36a64f"       # 緑
            }
            
            severity = violation_data.get("severity", "INFO")
            color = color_map.get(severity, "#808080")
            
            # Slack Block Kit形式でメッセージ構築
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚫 Quality Gate Violation - {severity}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Pattern:*\n{violation_data.get('pattern', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn", 
                            "text": f"*File:*\n{violation_data.get('file_path', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Tenant:*\n{violation_data.get('tenant_id', 'default')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Blocked:*\n{'✅ Yes' if violation_data.get('blocked') else '⚠️ No'}"
                        }
                    ]
                }
            ]
            
            # 詳細情報があれば追加
            if violation_data.get("message"):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Details:*\n```{violation_data['message']}```"
                    }
                })
            
            # アクションボタン追加
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Dashboard",
                            "emoji": True
                        },
                        "url": f"https://qualitygate.local/dashboard?violation_id={violation_data.get('id', '')}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Acknowledge",
                            "emoji": True
                        },
                        "action_id": "acknowledge_violation"
                    }
                ]
            })
            
            message = SlackMessage(
                channel=channel,
                text=f"Quality Gate Violation - {severity}",
                blocks=blocks
            )
            
            success = await self._send_message(message)
            
            processing_time = (time.time() - start_time) * 1000
            self._record_send_attempt(success, processing_time)
            
            return success
            
        except Exception as e:
            print(f"❌ Slack violation alert failed: {e}")
            self._record_send_attempt(False, (time.time() - start_time) * 1000)
            return False
    
    async def send_daily_report(
        self, 
        analytics_data: Dict[str, Any],
        channel: str = "#quality-reports"
    ) -> bool:
        """日次品質レポート送信"""
        start_time = time.time()
        
        try:
            # レポートブロック構築
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Quality Report",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Analyses:*\n{analytics_data.get('total_analyses', 0):,}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Violations Blocked:*\n{analytics_data.get('violations_blocked', 0):,}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Success Rate:*\n{analytics_data.get('success_rate_pct', 0):.1f}%"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Avg Response Time:*\n{analytics_data.get('avg_response_time_ms', 0):.2f}ms"
                        }
                    ]
                }
            ]
            
            # 違反内訳
            if analytics_data.get('violations_by_severity'):
                violations = analytics_data['violations_by_severity']
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Violations by Severity:*\n🔴 Critical: {violations.get('CRITICAL', 0)}\n🟡 High: {violations.get('HIGH', 0)}\n🔵 Info: {violations.get('INFO', 0)}"
                    }
                })
            
            message = SlackMessage(
                channel=channel,
                text="Daily Quality Report",
                blocks=blocks
            )
            
            success = await self._send_message(message)
            
            processing_time = (time.time() - start_time) * 1000
            self._record_send_attempt(success, processing_time)
            
            return success
            
        except Exception as e:
            print(f"❌ Slack daily report failed: {e}")
            return False
    
    async def send_custom_notification(
        self,
        message: str,
        channel: str,
        severity: str = "INFO",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """カスタム通知送信"""
        start_time = time.time()
        
        try:
            # 絵文字マッピング
            emoji_map = {
                "CRITICAL": "🚨",
                "HIGH": "⚠️",
                "INFO": "ℹ️",
                "SUCCESS": "✅"
            }
            
            emoji = emoji_map.get(severity, "📋")
            
            slack_message = SlackMessage(
                channel=channel,
                text=f"{emoji} {message}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{emoji} *{severity}*\n{message}"
                        }
                    }
                ]
            )
            
            # メタデータがあれば追加
            if metadata:
                metadata_text = "\n".join([f"*{k}:* {v}" for k, v in metadata.items()])
                slack_message.blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Details:*\n{metadata_text}"
                    }
                })
            
            success = await self._send_message(slack_message)
            
            processing_time = (time.time() - start_time) * 1000
            self._record_send_attempt(success, processing_time)
            
            return success
            
        except Exception as e:
            print(f"❌ Slack custom notification failed: {e}")
            return False
    
    async def _send_message(self, message: SlackMessage) -> bool:
        """メッセージ送信（内部）"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                payload = {
                    "channel": message.channel,
                    "text": message.text
                }
                
                if message.blocks:
                    payload["blocks"] = message.blocks
                
                if message.attachments:
                    payload["attachments"] = message.attachments
                
                if message.thread_ts:
                    payload["thread_ts"] = message.thread_ts
                
                if self.bot_token:
                    # Bot Token使用（Slack Web API）
                    headers = {
                        "Authorization": f"Bearer {self.bot_token}",
                        "Content-Type": "application/json"
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/chat.postMessage",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return result.get("ok", False)
                    
                else:
                    # Webhook URL使用
                    response = await client.post(
                        self.webhook_url,
                        json=payload
                    )
                    
                    return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Slack message send error: {e}")
            return False
        
        return False
    
    def _record_send_attempt(self, success: bool, response_time_ms: float):
        """送信試行記録"""
        self.integration_stats["messages_sent"] += 1
        
        if not success:
            self.integration_stats["failed_sends"] += 1
        
        # 平均応答時間更新
        total = self.integration_stats["messages_sent"]
        self.integration_stats["avg_response_time_ms"] = (
            (self.integration_stats["avg_response_time_ms"] * (total - 1) + response_time_ms) / total
        )
        
        # パフォーマンス制約チェック
        if response_time_ms > self.max_response_time_ms:
            print(f"⚠️ SLACK WARNING: Response time {response_time_ms:.2f}ms exceeds {self.max_response_time_ms}ms limit")
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """統合統計取得"""
        total = self.integration_stats["messages_sent"]
        if total == 0:
            success_rate = 0.0
        else:
            success_rate = ((total - self.integration_stats["failed_sends"]) / total) * 100
        
        return {
            **self.integration_stats,
            "success_rate_pct": success_rate,
            "performance_constraint_ms": self.max_response_time_ms
        }


# 使用例とテスト用ヘルパー
async def test_slack_integration():
    """Slack統合テスト"""
    
    # テスト用ダミーWebhook URL
    webhook_url = "https://hooks.slack.com/services/TEST/TEST/TEST"
    
    slack = SlackIntegration(webhook_url)
    
    # 違反アラートテスト
    violation_data = {
        "id": "violation_001",
        "severity": "CRITICAL", 
        "pattern": "Hardcoded API Secret",
        "file_path": "config/settings.py",
        "message": "'sk_live_abc123' detected in source code",
        "blocked": True,
        "tenant_id": "sample-tenant-001"
    }
    
    print("🧪 Testing Slack violation alert...")
    success = await slack.send_violation_alert(violation_data)
    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
    
    # 日次レポートテスト
    analytics_data = {
        "total_analyses": 1250,
        "violations_blocked": 15,
        "success_rate_pct": 98.8,
        "avg_response_time_ms": 0.85,
        "violations_by_severity": {
            "CRITICAL": 15,
            "HIGH": 89,
            "INFO": 234
        }
    }
    
    print("🧪 Testing Slack daily report...")
    success = await slack.send_daily_report(analytics_data)
    print(f"Result: {'✅ Success' if success else '❌ Failed'}")
    
    # 統計表示
    stats = slack.get_integration_stats()
    print(f"📊 Integration Stats: {stats}")


if __name__ == "__main__":
    asyncio.run(test_slack_integration())
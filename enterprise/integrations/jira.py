#!/usr/bin/env python3
"""
QualityGate JIRA Integration
Automatic issue creation for quality violations
"""

import time
import asyncio
import json
import base64
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import httpx
from fastapi import HTTPException


@dataclass
class JIRAIssue:
    """JIRA Issue構造"""
    project_key: str
    summary: str
    description: str
    issue_type: str = "Bug"
    priority: str = "Medium"
    labels: Optional[List[str]] = None
    assignee: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class JIRAIntegration:
    """JIRA統合クライアント"""
    
    def __init__(
        self, 
        base_url: str, 
        username: str, 
        api_token: str,
        default_project: str
    ):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.default_project = default_project
        
        # 認証ヘッダー準備
        auth_string = f"{username}:{api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_header = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # パフォーマンス制約
        self.max_response_time_ms = 5000  # 5秒以内
        
        # 統計
        self.integration_stats = {
            "issues_created": 0,
            "issues_updated": 0,
            "failed_operations": 0,
            "avg_response_time_ms": 0.0
        }
        
        # 重複防止キャッシュ
        self.recent_issues = {}  # violation_hash -> issue_key
    
    async def create_violation_issue(
        self, 
        violation_data: Dict[str, Any],
        project_key: Optional[str] = None
    ) -> Optional[str]:
        """品質違反Issue作成"""
        start_time = time.time()
        
        try:
            project = project_key or self.default_project
            
            # 重複チェック
            violation_hash = self._generate_violation_hash(violation_data)
            if violation_hash in self.recent_issues:
                print(f"⚠️ Duplicate violation detected, skipping JIRA issue creation")
                return self.recent_issues[violation_hash]
            
            # 優先度マッピング
            priority_map = {
                "CRITICAL": "Highest",
                "HIGH": "High", 
                "INFO": "Low"
            }
            
            severity = violation_data.get("severity", "INFO")
            priority = priority_map.get(severity, "Medium")
            
            # Issue詳細構築
            summary = f"Quality Gate Violation: {violation_data.get('pattern', 'Unknown Pattern')}"
            
            description = self._build_violation_description(violation_data)
            
            labels = [
                "qualitygate",
                f"severity-{severity.lower()}",
                f"tenant-{violation_data.get('tenant_id', 'default')}"
            ]
            
            if violation_data.get('blocked'):
                labels.append("blocked")
            
            issue = JIRAIssue(
                project_key=project,
                summary=summary,
                description=description,
                issue_type="Bug",
                priority=priority,
                labels=labels
            )
            
            issue_key = await self._create_issue(issue)
            
            if issue_key:
                # 重複防止キャッシュに追加
                self.recent_issues[violation_hash] = issue_key
                
                # キャッシュサイズ制限（最新100件）
                if len(self.recent_issues) > 100:
                    oldest_key = list(self.recent_issues.keys())[0]
                    del self.recent_issues[oldest_key]
                
                print(f"✅ JIRA issue created: {issue_key}")
            
            processing_time = (time.time() - start_time) * 1000
            self._record_operation("create", issue_key is not None, processing_time)
            
            return issue_key
            
        except Exception as e:
            print(f"❌ JIRA issue creation failed: {e}")
            self._record_operation("create", False, (time.time() - start_time) * 1000)
            return None
    
    async def update_issue_status(
        self, 
        issue_key: str, 
        status: str,
        comment: Optional[str] = None
    ) -> bool:
        """Issue状態更新"""
        start_time = time.time()
        
        try:
            # 利用可能なトランジション取得
            transitions = await self._get_available_transitions(issue_key)
            
            target_transition = None
            for transition in transitions:
                if transition["to"]["name"].lower() == status.lower():
                    target_transition = transition
                    break
            
            if not target_transition:
                print(f"⚠️ Transition to '{status}' not available for issue {issue_key}")
                return False
            
            # ステータス更新実行
            payload = {
                "transition": {
                    "id": target_transition["id"]
                }
            }
            
            # コメント追加
            if comment:
                payload["update"] = {
                    "comment": [
                        {
                            "add": {
                                "body": comment
                            }
                        }
                    ]
                }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                    headers=self.headers,
                    json=payload
                )
                
                success = response.status_code == 204
            
            processing_time = (time.time() - start_time) * 1000
            self._record_operation("update", success, processing_time)
            
            if success:
                print(f"✅ JIRA issue {issue_key} status updated to {status}")
            
            return success
            
        except Exception as e:
            print(f"❌ JIRA issue update failed: {e}")
            self._record_operation("update", False, (time.time() - start_time) * 1000)
            return False
    
    async def add_comment(
        self, 
        issue_key: str, 
        comment: str,
        visibility: Optional[str] = None
    ) -> bool:
        """Issueコメント追加"""
        start_time = time.time()
        
        try:
            payload = {
                "body": comment
            }
            
            if visibility:
                payload["visibility"] = {
                    "type": "group",
                    "value": visibility
                }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                    headers=self.headers,
                    json=payload
                )
                
                success = response.status_code == 201
            
            processing_time = (time.time() - start_time) * 1000
            self._record_operation("comment", success, processing_time)
            
            return success
            
        except Exception as e:
            print(f"❌ JIRA comment addition failed: {e}")
            return False
    
    async def search_quality_issues(
        self,
        project_key: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """品質関連Issue検索"""
        start_time = time.time()
        
        try:
            project = project_key or self.default_project
            
            # JQL構築
            jql_parts = [
                f'project = "{project}"',
                'labels = "qualitygate"'
            ]
            
            if severity:
                jql_parts.append(f'labels = "severity-{severity.lower()}"')
            
            jql = " AND ".join(jql_parts)
            
            params = {
                "jql": jql,
                "maxResults": limit,
                "fields": ["summary", "status", "priority", "created", "updated", "labels"]
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/search",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    issues = result.get("issues", [])
                    
                    # 必要な情報を抽出
                    processed_issues = []
                    for issue in issues:
                        processed_issues.append({
                            "key": issue["key"],
                            "summary": issue["fields"]["summary"],
                            "status": issue["fields"]["status"]["name"],
                            "priority": issue["fields"]["priority"]["name"],
                            "created": issue["fields"]["created"],
                            "updated": issue["fields"]["updated"],
                            "labels": issue["fields"]["labels"]
                        })
                    
                    processing_time = (time.time() - start_time) * 1000
                    
                    # パフォーマンス制約チェック
                    if processing_time > self.max_response_time_ms:
                        print(f"⚠️ JIRA WARNING: Search took {processing_time:.2f}ms exceeds {self.max_response_time_ms}ms limit")
                    
                    return processed_issues
                else:
                    print(f"❌ JIRA search failed: {response.status_code}")
                    return []
                    
        except Exception as e:
            print(f"❌ JIRA search error: {e}")
            return []
    
    async def _create_issue(self, issue: JIRAIssue) -> Optional[str]:
        """Issue作成（内部）"""
        try:
            payload = {
                "fields": {
                    "project": {"key": issue.project_key},
                    "summary": issue.summary,
                    "description": issue.description,
                    "issuetype": {"name": issue.issue_type},
                    "priority": {"name": issue.priority}
                }
            }
            
            if issue.labels:
                payload["fields"]["labels"] = issue.labels
            
            if issue.assignee:
                payload["fields"]["assignee"] = {"name": issue.assignee}
            
            if issue.custom_fields:
                payload["fields"].update(issue.custom_fields)
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}/rest/api/3/issue",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 201:
                    result = response.json()
                    return result["key"]
                else:
                    print(f"❌ JIRA issue creation failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ JIRA create issue error: {e}")
            return None
    
    async def _get_available_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """利用可能なトランジション取得"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("transitions", [])
                else:
                    return []
                    
        except Exception as e:
            print(f"❌ JIRA transitions error: {e}")
            return []
    
    def _build_violation_description(self, violation_data: Dict[str, Any]) -> str:
        """違反Issue説明文構築"""
        description_parts = [
            "h2. Quality Gate Violation Details",
            "",
            f"*Severity:* {violation_data.get('severity', 'Unknown')}",
            f"*Pattern:* {violation_data.get('pattern', 'Unknown')}",
            f"*File:* {violation_data.get('file_path', 'Unknown')}",
            f"*Tenant:* {violation_data.get('tenant_id', 'default')}",
            f"*Blocked:* {'Yes' if violation_data.get('blocked') else 'No'}",
            ""
        ]
        
        if violation_data.get('message'):
            description_parts.extend([
                "h3. Violation Message",
                "{code}",
                violation_data['message'],
                "{code}",
                ""
            ])
        
        if violation_data.get('timestamp'):
            description_parts.extend([
                f"*Detected At:* {violation_data['timestamp']}",
                ""
            ])
        
        description_parts.extend([
            "h3. Next Steps",
            "# Review the detected pattern and assess if it's a legitimate issue",
            "# If it's a false positive, add an exception to the Quality Gate rules",
            "# If it's a real issue, fix the code and verify the solution",
            "# Update this issue with the resolution details",
            "",
            "_This issue was automatically created by QualityGate Enterprise._"
        ])
        
        return "\n".join(description_parts)
    
    def _generate_violation_hash(self, violation_data: Dict[str, Any]) -> str:
        """違反データハッシュ生成（重複検出用）"""
        key_fields = [
            violation_data.get('pattern', ''),
            violation_data.get('file_path', ''),
            violation_data.get('tenant_id', ''),
            violation_data.get('severity', '')
        ]
        
        hash_string = "|".join(key_fields)
        return str(hash(hash_string))
    
    def _record_operation(self, operation: str, success: bool, response_time_ms: float):
        """操作記録"""
        if operation == "create":
            self.integration_stats["issues_created"] += 1
        elif operation == "update":
            self.integration_stats["issues_updated"] += 1
        
        if not success:
            self.integration_stats["failed_operations"] += 1
        
        # 平均応答時間更新
        total_ops = (self.integration_stats["issues_created"] + 
                    self.integration_stats["issues_updated"])
        
        if total_ops > 0:
            self.integration_stats["avg_response_time_ms"] = (
                (self.integration_stats["avg_response_time_ms"] * (total_ops - 1) + response_time_ms) / total_ops
            )
        
        # パフォーマンス制約チェック
        if response_time_ms > self.max_response_time_ms:
            print(f"⚠️ JIRA WARNING: {operation} operation took {response_time_ms:.2f}ms exceeds {self.max_response_time_ms}ms limit")
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """統合統計取得"""
        total_ops = (self.integration_stats["issues_created"] + 
                    self.integration_stats["issues_updated"])
        
        if total_ops == 0:
            success_rate = 0.0
        else:
            success_rate = ((total_ops - self.integration_stats["failed_operations"]) / total_ops) * 100
        
        return {
            **self.integration_stats,
            "success_rate_pct": success_rate,
            "performance_constraint_ms": self.max_response_time_ms,
            "recent_issues_cached": len(self.recent_issues)
        }


# 使用例とテスト
async def test_jira_integration():
    """JIRA統合テスト"""
    
    # テスト用設定（実際の値に置き換えが必要）
    jira = JIRAIntegration(
        base_url="https://your-domain.atlassian.net",
        username="test@example.com",
        api_token="your-api-token", 
        default_project="QG"
    )
    
    # 違反Issue作成テスト
    violation_data = {
        "id": "violation_002",
        "severity": "CRITICAL",
        "pattern": "Hardcoded Database Password",
        "file_path": "config/database.py",
        "message": "database_password = 'secret123' detected",
        "blocked": True,
        "tenant_id": "sample-tenant-001",
        "timestamp": "2025-08-02T23:45:00Z"
    }
    
    print("🧪 Testing JIRA issue creation...")
    issue_key = await jira.create_violation_issue(violation_data)
    print(f"Result: {'✅ Success - ' + issue_key if issue_key else '❌ Failed'}")
    
    if issue_key:
        # コメント追加テスト
        print("🧪 Testing JIRA comment addition...")
        success = await jira.add_comment(
            issue_key, 
            "Quality Gate has automatically detected this violation. Please review and address."
        )
        print(f"Result: {'✅ Success' if success else '❌ Failed'}")
    
    # Issue検索テスト
    print("🧪 Testing JIRA issue search...")
    issues = await jira.search_quality_issues(severity="CRITICAL", limit=10)
    print(f"Result: Found {len(issues)} issues")
    
    # 統計表示
    stats = jira.get_integration_stats()
    print(f"📊 Integration Stats: {stats}")


if __name__ == "__main__":
    asyncio.run(test_jira_integration())
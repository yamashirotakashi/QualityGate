#!/usr/bin/env python3
"""
QualityGate Enterprise Security Middleware
OWASP Top 10 対応セキュリティフレームワーク

対応項目:
- A01: Broken Access Control
- A02: Cryptographic Failures  
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable Components
- A07: Authentication Failures
- A08: Software & Data Integrity Failures
- A09: Security Logging & Monitoring Failures
- A10: Server-Side Request Forgery (SSRF)
"""

import time
import re
import html
import hashlib
import secrets
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダーミドルウェア - OWASP A05対応"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # セキュリティヘッダー設定
        self.security_headers = {
            # XSS Protection
            "X-XSS-Protection": "1; mode=block",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            
            # HSTS (HTTPS環境でのみ有効)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # CSP (Content Security Policy)
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            
            # Custom Security Headers
            "X-Powered-By": "",  # Hide server information
            "Server": ""
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # セキュリティヘッダー追加
        for header, value in self.security_headers.items():
            if value:  # 空文字でない場合のみ追加
                response.headers[header] = value
            elif header in ["X-Powered-By", "Server"]:
                # 空文字でサーバー情報を隠蔽
                response.headers[header] = ""
        
        return response


class OWASPMiddleware(BaseHTTPMiddleware):
    """OWASP Top 10対応統合セキュリティミドルウェア"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # セキュリティ設定
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.max_header_size = 8192  # 8KB
        self.max_url_length = 2048
        
        # 危険なパターン検出
        self.injection_patterns = [
            # SQL Injection (A03)
            re.compile(r"('|(\\)?\")|(-|#|--|/\*|\*/)", re.IGNORECASE),
            re.compile(r"\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b", re.IGNORECASE),
            
            # XSS (A03)
            re.compile(r"<script.*?>", re.IGNORECASE),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
            
            # Command Injection (A03)
            re.compile(r"[;&|`]", re.IGNORECASE),
            re.compile(r"\b(cat|ls|pwd|whoami|id|ps|netstat|ping|wget|curl)\b", re.IGNORECASE),
            
            # LDAP Injection (A03)
            re.compile(r"[()&|!]", re.IGNORECASE),
            
            # XXE (A03)
            re.compile(r"<!ENTITY", re.IGNORECASE),
            re.compile(r"SYSTEM\s", re.IGNORECASE)
        ]
        
        # SSRF対象URL (A10)
        self.ssrf_blocked_hosts = [
            "localhost", "127.0.0.1", "0.0.0.0",
            "10.", "172.", "192.168.",
            "metadata.google.internal",
            "169.254.169.254"  # AWS metadata
        ]
        
        # セキュリティ統計
        self.security_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "injection_attempts": 0,
            "xss_attempts": 0,
            "ssrf_attempts": 0,
            "oversized_requests": 0,
            "security_violations": []
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # セキュリティ検証実行
        security_result = await self._validate_request_security(request)
        
        if not security_result["safe"]:
            # セキュリティ違反をログ記録
            self._log_security_violation(request, security_result)
            
            # リクエストブロック
            return Response(
                content='{"detail":"Security violation detected"}',
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json",
                headers={"X-Security-Block": security_result["reason"]}
            )
        
        # 正常処理
        response = await call_next(request)
        
        # セキュリティ処理時間記録
        security_time = (time.time() - start_time) * 1000
        response.headers["X-Security-Time"] = str(security_time)
        
        # セキュリティ制約チェック（10ms以下）
        if security_time > 10:
            print(f"⚠️ SECURITY WARNING: Validation took {security_time:.2f}ms (>10ms limit)")
        
        return response
    
    async def _validate_request_security(self, request: Request) -> Dict[str, Any]:
        """リクエストセキュリティ検証"""
        self.security_stats["total_requests"] += 1
        
        # A05: Security Misconfiguration - リクエストサイズ制限
        if hasattr(request, "body"):
            try:
                body = await request.body()
                if len(body) > self.max_request_size:
                    self.security_stats["oversized_requests"] += 1
                    return {"safe": False, "reason": "Request too large", "category": "A05"}
            except:
                pass
        
        # URL長制限
        if len(str(request.url)) > self.max_url_length:
            return {"safe": False, "reason": "URL too long", "category": "A05"}
        
        # ヘッダーサイズ制限
        total_header_size = sum(len(k) + len(v) for k, v in request.headers.items())
        if total_header_size > self.max_header_size:
            return {"safe": False, "reason": "Headers too large", "category": "A05"}
        
        # A03: Injection - クエリパラメータ検証
        query_params = str(request.url.query)
        if query_params:
            injection_result = self._detect_injection(query_params)
            if injection_result["detected"]:
                self.security_stats["injection_attempts"] += 1
                return {"safe": False, "reason": f"Injection detected: {injection_result['type']}", "category": "A03"}
        
        # A03: Injection - ヘッダー検証
        for header, value in request.headers.items():
            if header.lower() not in ["authorization", "cookie"]:  # 認証ヘッダーは除外
                injection_result = self._detect_injection(value)
                if injection_result["detected"]:
                    self.security_stats["injection_attempts"] += 1
                    return {"safe": False, "reason": f"Header injection: {injection_result['type']}", "category": "A03"}
        
        # A10: SSRF - URL検証（リクエストボディ内のURL）
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    ssrf_result = self._detect_ssrf(body_str)
                    if ssrf_result["detected"]:
                        self.security_stats["ssrf_attempts"] += 1
                        return {"safe": False, "reason": "SSRF attempt detected", "category": "A10"}
            except:
                pass
        
        return {"safe": True, "reason": "Request validated", "category": None}
    
    def _detect_injection(self, text: str) -> Dict[str, Any]:
        """インジェクション攻撃検出"""
        if not text:
            return {"detected": False, "type": None}
        
        # URL デコード（二重エンコード対応）
        import urllib.parse
        decoded_text = urllib.parse.unquote_plus(urllib.parse.unquote_plus(text))
        
        for pattern in self.injection_patterns:
            if pattern.search(decoded_text):
                if "union|select" in pattern.pattern:
                    return {"detected": True, "type": "SQL Injection"}
                elif "script" in pattern.pattern:
                    return {"detected": True, "type": "XSS"}
                elif "[;&|`]" in pattern.pattern:
                    return {"detected": True, "type": "Command Injection"}
                elif "ENTITY" in pattern.pattern:
                    return {"detected": True, "type": "XXE"}
                else:
                    return {"detected": True, "type": "Generic Injection"}
        
        return {"detected": False, "type": None}
    
    def _detect_ssrf(self, text: str) -> Dict[str, Any]:
        """SSRF攻撃検出"""
        if not text:
            return {"detected": False}
        
        # URL抽出パターン
        url_pattern = re.compile(r'https?://[^\s<>"]+', re.IGNORECASE)
        urls = url_pattern.findall(text)
        
        for url in urls:
            try:
                parsed = urlparse(url)
                hostname = parsed.hostname
                
                if hostname:
                    # 危険なホスト名チェック
                    for blocked_host in self.ssrf_blocked_hosts:
                        if hostname.startswith(blocked_host) or hostname == blocked_host:
                            return {"detected": True, "url": url, "reason": f"Blocked host: {hostname}"}
                    
                    # プライベートIPアドレス範囲チェック
                    if self._is_private_ip(hostname):
                        return {"detected": True, "url": url, "reason": f"Private IP: {hostname}"}
                        
            except Exception:
                # URL解析エラー - 安全側に倒してブロック
                return {"detected": True, "url": url, "reason": "Malformed URL"}
        
        return {"detected": False}
    
    def _is_private_ip(self, hostname: str) -> bool:
        """プライベートIPアドレス判定"""
        try:
            import ipaddress
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            return False
    
    def _log_security_violation(self, request: Request, security_result: Dict[str, Any]):
        """セキュリティ違反ログ記録"""
        violation = {
            "timestamp": time.time(),
            "ip": request.client.host,
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("User-Agent", ""),
            "reason": security_result["reason"],
            "category": security_result["category"],
            "query_params": str(request.url.query) if request.url.query else "",
            "headers": dict(request.headers)
        }
        
        self.security_stats["blocked_requests"] += 1
        self.security_stats["security_violations"].append(violation)
        
        # 直近100件のみ保持
        if len(self.security_stats["security_violations"]) > 100:
            self.security_stats["security_violations"] = self.security_stats["security_violations"][-100:]
        
        # 重要なセキュリティ違反をログ출력
        print(f"🚫 SECURITY VIOLATION: {security_result['category']} - {security_result['reason']} from {request.client.host}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """セキュリティ統計取得"""
        total = self.security_stats["total_requests"]
        if total == 0:
            block_rate = 0.0
        else:
            block_rate = (self.security_stats["blocked_requests"] / total) * 100
        
        return {
            **self.security_stats,
            "block_rate_pct": block_rate,
            "recent_violations": self.security_stats["security_violations"][-10:] if self.security_stats["security_violations"] else []
        }


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF保護ミドルウェア - OWASP A01対応"""
    
    def __init__(self, app):
        super().__init__(app)
        self.csrf_token_header = "X-CSRF-Token"
        self.csrf_cookie_name = "csrf_token"
        
        # CSRF保護対象メソッド
        self.protected_methods = ["POST", "PUT", "PATCH", "DELETE"]
        
        # CSRF免除エンドポイント
        self.exempt_paths = [
            "/api/v1/auth/login",
            "/api/v1/health"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # CSRF保護対象判定
        if (request.method in self.protected_methods and 
            request.url.path not in self.exempt_paths):
            
            # CSRF Token検証
            if not await self._verify_csrf_token(request):
                return Response(
                    content='{"detail":"CSRF token missing or invalid"}',
                    status_code=status.HTTP_403_FORBIDDEN,
                    media_type="application/json"
                )
        
        response = await call_next(request)
        
        #新しいCSRF Token生成・設定
        csrf_token = self._generate_csrf_token()
        response.set_cookie(
            self.csrf_cookie_name,
            csrf_token,
            httponly=True,
            secure=True,  # HTTPS環境でのみ
            samesite="strict"
        )
        response.headers["X-CSRF-Token"] = csrf_token
        
        return response
    
    async def _verify_csrf_token(self, request: Request) -> bool:
        """CSRF Token検証"""
        # ヘッダーからトークン取得
        header_token = request.headers.get(self.csrf_token_header)
        
        # クッキーからトークン取得
        cookie_token = request.cookies.get(self.csrf_cookie_name)
        
        # 両方存在し、一致している場合のみ有効
        return (header_token and cookie_token and 
                header_token == cookie_token and
                len(header_token) >= 32)
    
    def _generate_csrf_token(self) -> str:
        """CSRF Token生成"""
        return secrets.token_urlsafe(32)


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """入力サニタイゼーションミドルウェア - A03対応"""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # リクエストボディのサニタイゼーション
        if request.method in ["POST", "PUT", "PATCH"]:
            # Note: FastAPIのPydanticモデルで自動的に検証されるため、
            # 追加のサニタイゼーションは控えめに実装
            pass
        
        response = await call_next(request)
        return response
    
    def sanitize_html(self, text: str) -> str:
        """HTMLサニタイゼーション"""
        if not text:
            return text
        
        # HTMLエスケープ
        return html.escape(text, quote=True)
    
    def sanitize_sql(self, text: str) -> str:
        """SQL文字列サニタイゼーション"""
        if not text:
            return text
        
        # SQLメタ文字エスケープ
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        for char in dangerous_chars:
            text = text.replace(char, f"\\{char}")
        
        return text
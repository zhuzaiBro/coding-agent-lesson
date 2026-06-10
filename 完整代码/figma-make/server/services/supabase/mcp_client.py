"""
Supabase Remote MCP 客户端（JSON-RPC over HTTP）。

认证：浏览器 OAuth 会话 token 或环境变量 SUPABASE_ACCESS_TOKEN。
常用工具：list_tables、execute_sql、apply_migration、get_project_url 等。
文档：https://supabase.com/docs/guides/ai-tools/mcp
"""
import json
import os
from typing import Any, Dict, Optional

import httpx

from config.supabase import (
    build_mcp_url,
    extract_project_ref_from_url,
    get_access_token,
    get_project_ref,
    has_project_ref,
    is_supabase_configured,
    missing_project_ref_message,
    set_runtime_project_ref,
)

_client_instance: Optional["SupabaseMCPClient"] = None


def extract_mcp_tool_text(result: Any) -> str:
    """Normalize MCP tools/call result to plain text for LLM prompts."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                    elif "text" in item:
                        parts.append(str(item["text"]))
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return "\n".join(parts)
        for key in ("text", "code", "data", "message"):
            if key in result and result[key]:
                value = result[key]
                if isinstance(value, str):
                    return value
        return json.dumps(result, ensure_ascii=False, indent=2)
    if isinstance(result, list):
        return "\n".join(extract_mcp_tool_text(item) for item in result)
    return str(result)


class SupabaseMCPClient:
    """HTTP JSON-RPC client for Supabase MCP (streamable HTTP transport)."""

    def __init__(
        self,
        url: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        if not is_supabase_configured() and not (url and access_token):
            raise RuntimeError(
                "Supabase MCP is not configured. Set SUPABASE_ACCESS_TOKEN and "
                "SUPABASE_PROJECT_REF in server/.env"
            )
        self.url = url or build_mcp_url()
        self.access_token = access_token or get_access_token()
        self._session_id: Optional[str] = None
        self._message_id = 0
        self._initialized = False

    def _next_id(self) -> int:
        self._message_id += 1
        return self._message_id

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.url,
                json=payload,
                headers=self._headers(),
            )

            if "mcp-session-id" in response.headers:
                self._session_id = response.headers["mcp-session-id"]

            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                return self._parse_sse_response(response.text)
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"Supabase MCP error: {data['error']}")
            return data.get("result")

    def _parse_sse_response(self, text: str) -> Any:
        for line in text.strip().split("\n"):
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            if "error" in data:
                raise RuntimeError(f"Supabase MCP SSE error: {data['error']}")
            return data.get("result")
        return None

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "figma-make-server", "version": "1.0.0"},
                "capabilities": {},
            },
        )
        self._initialized = True
        print(f"[SupabaseMCPClient] Connected to {self.url}")

        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(self.url, json=payload, headers=self._headers())
        except Exception:
            pass

    def _rebind_scoped_url(self) -> None:
        """project_ref 解析后切换为带 project_ref 的 MCP URL。"""
        new_url = build_mcp_url()
        if new_url != self.url:
            self.url = new_url
            self._initialized = False
            self._session_id = None

    async def ensure_project_scoped(self) -> str:
        """
        确保 MCP URL 含 project_ref（list_tables / execute_sql 必需）。

        优先级：.env > OAuth 会话选择 > get_project_url 自动解析。
        """
        if has_project_ref():
            self._rebind_scoped_url()
            await self.initialize()
            return get_project_ref()

        await self.initialize()
        result = await self._send_request(
            "tools/call",
            {"name": "get_project_url", "arguments": {}},
        )
        project_url = extract_mcp_tool_text(result).strip()
        discovered = extract_project_ref_from_url(project_url)
        if not discovered:
            raise RuntimeError(missing_project_ref_message())

        set_runtime_project_ref(discovered)
        self._rebind_scoped_url()
        await self.initialize()
        return discovered

    async def call_tool_raw(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用 MCP 工具，不强制 project_ref（用于 list_projects 等账号级工具）。"""
        await self.initialize()
        result = await self._send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )
        return extract_mcp_tool_text(result)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        await self.initialize()
        if tool_name not in ("get_project_url", "list_projects"):
            await self.ensure_project_scoped()
        result = await self._send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )
        return extract_mcp_tool_text(result)

    async def list_projects(self) -> str:
        return await self.call_tool_raw("list_projects", {})

    async def list_tables(self, *, verbose: bool = True, schemas: Optional[list] = None) -> str:
        return await self.call_tool(
            "list_tables",
            {
                "schemas": schemas or ["public"],
                "verbose": verbose,
            },
        )

    async def get_project_url(self) -> str:
        return await self.call_tool("get_project_url", {})

    async def get_publishable_keys(self) -> str:
        return await self.call_tool("get_publishable_keys", {})

    async def generate_typescript_types(self) -> str:
        return await self.call_tool("generate_typescript_types", {})

    async def search_docs(self, graphql_query: str) -> str:
        return await self.call_tool("search_docs", {"graphql_query": graphql_query})

    async def execute_sql(self, query: str) -> str:
        return await self.call_tool("execute_sql", {"query": query})

    async def list_migrations(self) -> str:
        return await self.call_tool("list_migrations", {})

    async def apply_migration(self, name: str, query: str) -> str:
        """DDL：建表/改表/索引等（需 MCP 非 read_only 且 OAuth 含 database:write）。"""
        return await self.call_tool(
            "apply_migration",
            {"name": name, "query": query},
        )

    async def get_advisors(self, advisor_type: str = "security") -> str:
        return await self.call_tool("get_advisors", {"type": advisor_type})

    async def ping(self) -> Dict[str, Any]:
        """连通性检查：解析 project_ref 并尝试拉取表结构。"""
        project_ref = await self.ensure_project_scoped()
        project_url = (await self.get_project_url()).strip()
        schema_ready = False
        schema_error = ""
        try:
            preview = await self.list_tables(verbose=False)
            schema_ready = bool(preview and "project_id" not in preview.lower())
        except Exception as error:
            schema_error = str(error)[:500]

        payload: Dict[str, Any] = {
            "ok": True,
            "projectUrl": project_url,
            "projectRef": project_ref,
            "mcpUrl": self.url,
            "schemaReady": schema_ready,
        }
        if not schema_ready:
            payload["ok"] = False
            payload["message"] = schema_error or missing_project_ref_message()
        return payload


def get_supabase_mcp_client() -> SupabaseMCPClient:
    global _client_instance
    from config.supabase import get_access_token

    token = get_access_token()
    if _client_instance is not None and getattr(_client_instance, "access_token", "") != token:
        reset_supabase_mcp_client()
    if _client_instance is None:
        _client_instance = SupabaseMCPClient(access_token=token or None)
    return _client_instance


def reset_supabase_mcp_client() -> None:
    """Reset singleton（测试、配置重载或 OAuth 登出）。"""
    global _client_instance
    from config.supabase import clear_runtime_project_ref

    _client_instance = None
    clear_runtime_project_ref()

"""
Figma MCP Client.

Communicates with local Figma Desktop MCP Server via HTTP JSON-RPC.
Default endpoint: http://127.0.0.1:3845/mcp
"""
import json
import os
from typing import Any, Dict, Optional

import httpx

from config.figma import get_access_token, get_mcp_mode, get_mcp_url

DEFAULT_FIGMA_MCP_URL = "http://127.0.0.1:3845/mcp"

# Singleton
_client_instance: Optional["FigmaMCPClient"] = None


class FigmaMCPClient:
    """Figma MCP Client using HTTP JSON-RPC transport."""

    def __init__(self, url: Optional[str] = None, access_token: Optional[str] = None):
        self.url = url or get_mcp_url()
        self.access_token = access_token if access_token is not None else get_access_token()
        self._session_id: Optional[str] = None
        self._message_id = 0
        self._initialized = False

    def _next_id(self) -> int:
        self._message_id += 1
        return self._message_id

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a JSON-RPC request to the MCP server."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(self.url, json=payload, headers=headers)

            # Save session ID if provided
            if "mcp-session-id" in response.headers:
                self._session_id = response.headers["mcp-session-id"]

            response.raise_for_status()

            # Handle SSE or plain JSON response
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                return self._parse_sse_response(response.text)
            else:
                data = response.json()
                if "error" in data:
                    raise RuntimeError(f"MCP Error: {data['error']}")
                return data.get("result")

    def _parse_sse_response(self, text: str) -> Any:
        """Parse SSE (Server-Sent Events) response."""
        lines = text.strip().split("\n")
        for line in lines:
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str and data_str != "[DONE]":
                    try:
                        data = json.loads(data_str)
                        if "error" in data:
                            raise RuntimeError(f"MCP SSE Error: {data['error']}")
                        return data.get("result")
                    except json.JSONDecodeError:
                        continue
        return None

    async def initialize(self) -> None:
        """Initialize the MCP session."""
        if self._initialized:
            return
        try:
            result = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "figma-make-server", "version": "1.0.0"},
                "capabilities": {},
            })
            self._initialized = True
            print(f"[FigmaMCPClient] Connected to Figma MCP at {self.url}")

            await self._send_initialized_notification()
        except Exception as e:
            mode = get_mcp_mode()
            hint = (
                "Figma Desktop 已打开设计稿并在 Dev Mode 启用 MCP"
                if mode == "desktop"
                else "已完成 Figma 浏览器 OAuth 授权（FIGMA_MCP_MODE=remote）"
            )
            raise RuntimeError(
                f"Failed to connect to Figma MCP ({mode}): {e}\n"
                f"请确认：{hint}\n"
                f"MCP 地址：{self.url}"
            ) from e

    async def _send_initialized_notification(self) -> None:
        """Send the initialized notification (fire-and-forget)."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
            headers = {"Content-Type": "application/json"}
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(self.url, json=payload, headers=headers)
        except Exception:
            pass  # Notification is fire-and-forget

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return result

    async def get_generated_code(self, figma_url: str) -> str:
        """
        Get generated React code from a Figma design URL.

        Uses the get_design_context tool from Figma MCP.
        """
        print(f"[FigmaMCPClient] Calling get_design_context for: {figma_url}")

        # Initialize session if needed
        await self.initialize()

        # Call the Figma MCP tool
        result = await self.call_tool("get_design_context", {"url": figma_url})

        if not result:
            raise ValueError("Figma MCP returned empty result")

        # Extract code from result
        if isinstance(result, dict):
            # Try common result fields
            code = (
                result.get("code") or
                result.get("content") or
                result.get("data") or
                ""
            )
            if isinstance(code, list):
                # content array format
                code = "\n".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in code
                )
        elif isinstance(result, str):
            code = result
        elif isinstance(result, list):
            # content array
            code = "\n".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in result
            )
        else:
            code = str(result)

        if not code:
            raise ValueError("Figma MCP returned empty code")

        return code

    async def ping(self) -> Dict[str, Any]:
        await self.initialize()
        tools: list[str] = []
        try:
            result = await self._send_request("tools/list", {})
            if isinstance(result, dict) and isinstance(result.get("tools"), list):
                tools = [
                    str(t.get("name", ""))
                    for t in result["tools"]
                    if isinstance(t, dict) and t.get("name")
                ]
        except Exception:
            tools = ["get_design_context"]

        return {
            "ok": True,
            "mcpUrl": self.url,
            "mode": get_mcp_mode(),
            "tools": tools or ["get_design_context"],
        }


def get_figma_mcp_client() -> FigmaMCPClient:
    """Get singleton FigmaMCPClient instance."""
    global _client_instance
    token = get_access_token()
    if _client_instance is not None and getattr(_client_instance, "access_token", "") != token:
        reset_figma_mcp_client()
    if _client_instance is None:
        _client_instance = FigmaMCPClient(access_token=token or None)
    return _client_instance


def reset_figma_mcp_client() -> None:
    global _client_instance
    _client_instance = None

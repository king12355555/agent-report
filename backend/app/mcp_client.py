"""MCP 客户端: 连接 MCP 工具服务(SSE) 并调用工具。"""
import json

from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    def __init__(self, url: str):
        self.url = url
        self.session: ClientSession | None = None
        self._sse_ctx = None
        self._session_ctx = None

    async def connect(self):
        self._sse_ctx = sse_client(self.url)
        read, write = await self._sse_ctx.__aenter__()
        self._session_ctx = ClientSession(read, write)
        self.session = await self._session_ctx.__aenter__()
        await self.session.initialize()

    async def close(self):
        if self._session_ctx:
            await self._session_ctx.__aexit__(None, None, None)
        if self._sse_ctx:
            await self._sse_ctx.__aexit__(None, None, None)

    async def call_tool(self, name: str, arguments: dict) -> str:
        if not self.session:
            raise RuntimeError("MCP 客户端未连接")
        result = await self.session.call_tool(name, arguments)
        parts = []
        for content in result.content:
            if getattr(content, "type", "") == "text":
                parts.append(content.text)
            elif getattr(content, "type", "") == "json":
                parts.append(json.dumps(content.data, ensure_ascii=False))
        return "\n".join(parts)

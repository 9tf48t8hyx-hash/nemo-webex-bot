"""
MCPManager -- Client MCP SSE pour les serveurs Nemo v2.
Repris du pattern de Nemo Web app_v2 / mcp_client.py.
"""
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPManager:

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._stacks: dict[str, AsyncExitStack] = {}
        self._tools: dict[str, str] = {}
        self._schemas: list[dict] = []

    async def connect_server(self, name: str, url: str):
        stack = AsyncExitStack()
        read, write = await stack.enter_async_context(sse_client(url))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._sessions[name] = session
        self._stacks[name] = stack
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            self._tools[tool.name] = name
            self._schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            })
        print(f"[MCP] {name} ({url}) : {len(tools_result.tools)} outil(s)")

    async def call_tool(self, tool_name: str, args: dict) -> str:
        server = self._tools.get(tool_name)
        if not server:
            return f"[Erreur] Outil inconnu : {tool_name}"
        try:
            result = await self._sessions[server].call_tool(tool_name, args)
            return "\n".join(
                block.text for block in result.content if hasattr(block, "text")
            )
        except Exception as e:
            return f"[Erreur] {tool_name} : {e}"

    def get_openai_tools(self) -> list[dict]:
        return list(self._schemas)

    def get_all_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    async def shutdown(self):
        for stack in self._stacks.values():
            try:
                await stack.aclose()
            except Exception:
                pass

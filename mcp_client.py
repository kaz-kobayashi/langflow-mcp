"""
MCP Client for integrating with AI Chat Agent
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class InventoryMCPClient:
    """在庫最適化MCPサーバーへのクライアント"""

    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.session = None

    async def connect(self):
        """MCPサーバーに接続"""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path],
            env=None
        )

        # stdio_client is an async context manager
        self.stdio_context = stdio_client(server_params)
        self.stdio, self.write = await self.stdio_context.__aenter__()
        self.session = ClientSession(self.stdio, self.write)

        await self.session.initialize()

        # 利用可能なツールを取得
        tools_response = await self.session.list_tools()
        return tools_response.tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """MCPツールを呼び出し"""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self.session.call_tool(tool_name, arguments)
        return result

    async def close(self):
        """接続を閉じる"""
        if hasattr(self, 'stdio_context'):
            await self.stdio_context.__aexit__(None, None, None)


async def test_mcp_client():
    """MCPクライアントのテスト"""
    client = InventoryMCPClient("/Users/kazuhiro/Documents/2510/langflow-mcp/mcp_inventory_server.py")

    # 接続
    tools = await client.connect()
    print("Available tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    # EOQ計算テスト
    print("\n=== Testing EOQ Calculation ===")
    result = await client.call_tool("calculate_eoq", {
        "K": 1000.0,
        "d": 100.0,
        "h": 1.0,
        "b": 100.0
    })
    print(json.dumps(result.content[0].text if result.content else {}, indent=2, ensure_ascii=False))

    # 安全在庫計算テスト
    print("\n=== Testing Safety Stock Calculation ===")
    result = await client.call_tool("calculate_safety_stock", {
        "mu": 100.0,
        "sigma": 10.0,
        "LT": 3,
        "b": 100.0,
        "h": 1.0
    })
    print(json.dumps(result.content[0].text if result.content else {}, indent=2, ensure_ascii=False))

    # ネットワーク分析テスト
    print("\n=== Testing Network Analysis ===")
    items_data = json.dumps([
        {
            "name": "製品A",
            "process_time": 1,
            "max_service_time": 3,
            "avg_demand": 100,
            "demand_std": 10,
            "holding_cost": 1,
            "stockout_cost": 100,
            "fixed_cost": 1000
        },
        {
            "name": "部品B",
            "process_time": 2,
            "max_service_time": 0,
            "avg_demand": None,
            "demand_std": None,
            "holding_cost": 0.5,
            "stockout_cost": 50,
            "fixed_cost": 500
        }
    ])

    bom_data = json.dumps([
        {"child": "部品B", "parent": "製品A", "quantity": 2}
    ])

    result = await client.call_tool("analyze_inventory_network", {
        "items_data": items_data,
        "bom_data": bom_data
    })
    print(json.dumps(json.loads(result.content[0].text) if result.content else {}, indent=2, ensure_ascii=False))

    # 接続を閉じる
    await client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())

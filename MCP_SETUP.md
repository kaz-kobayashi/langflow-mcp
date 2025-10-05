# サプライチェーン在庫最適化 MCP Server セットアップガイド

## 概要

このMCPサーバーは、`03inventory.ipynb`ノートブックの在庫最適化機能をFastMCPを使ってMCPプロトコルで提供します。

## 提供機能

### 1. 経済発注量（EOQ）計算
- ツール名: `calculate_eoq`
- 説明: 発注固定費用、平均需要、在庫保管費用などから最適発注量を計算

### 2. 安全在庫レベル計算
- ツール名: `calculate_safety_stock`
- 説明: リードタイム、需要の変動性を考慮した安全在庫レベルを計算

### 3. マルチエシュロン在庫最適化（MESSA）
- ツール名: `optimize_safety_stock_allocation`
- 説明: サプライチェーンネットワーク全体での最適な安全在庫配置を計算

### 4. 在庫ネットワーク分析
- ツール名: `analyze_inventory_network`
- 説明: サプライチェーンネットワークの構造とコスト情報を分析

## セットアップ方法

### 1. 必要なパッケージのインストール

```bash
pip install fastmcp mcp
```

### 2. MCPサーバーの起動確認

```bash
python mcp_inventory_server.py --help
```

正常に起動すると、FastMCPのバナーが表示されます。

### 3. Claude Desktop での統合

Claude Desktop の設定ファイルに以下を追加：

**macOS/Linux:** `~/.config/claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "python",
      "args": [
        "/Users/kazuhiro/Documents/2510/langflow-mcp/mcp_inventory_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/kazuhiro/Documents/2510/langflow-mcp"
      }
    }
  }
}
```

**注意:** パスは環境に合わせて変更してください。

### 4. AIチャットエージェントでの利用

現在のFastAPI + Alpine.js チャットアプリから MCP サーバーを呼び出すには、以下の2つの方法があります：

#### 方法1: OpenAI Function Calling を使用

`main.py` を拡張して、OpenAI の Function Calling 経由で MCP ツールを呼び出す：

```python
from mcp_client import InventoryMCPClient

# チャット endpoint 内で
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_eoq",
            "description": "経済発注量を計算",
            "parameters": {
                "type": "object",
                "properties": {
                    "K": {"type": "number", "description": "発注固定費用"},
                    "d": {"type": "number", "description": "平均需要量"},
                    "h": {"type": "number", "description": "在庫保管費用"},
                    "b": {"type": "number", "description": "品切れ費用"}
                },
                "required": ["K", "d", "h", "b"]
            }
        }
    }
]

# OpenAI API に tools パラメータを渡す
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    tools=tools,
    tool_choice="auto"
)
```

#### 方法2: 直接統合（Claude Desktop）

Claude Desktop アプリで本 MCP サーバーを設定すると、Claude がチャット中に自動的にツールを利用できます。

## 使用例

### EOQ計算の例

```python
{
  "K": 1000.0,    # 発注固定費用（円）
  "d": 100.0,     # 平均需要量（units/日）
  "h": 1.0,       # 在庫保管費用（円/unit/日）
  "b": 100.0      # 品切れ費用（円/unit/日）
}
```

結果:
```json
{
  "optimal_order_quantity": 447.21,
  "total_cost": 447.21,
  "parameters": {...}
}
```

### マルチエシュロン最適化の例

```json
{
  "items_data": "[{\"name\":\"製品A\",\"process_time\":1,\"avg_demand\":100,\"demand_std\":10,\"holding_cost\":1,\"stockout_cost\":100}]",
  "bom_data": "[{\"child\":\"部品B\",\"parent\":\"製品A\",\"quantity\":2}]"
}
```

## トラブルシューティング

### ModuleNotFoundError が出る場合

```bash
export PYTHONPATH=/Users/kazuhiro/Documents/2510/langflow-mcp:$PYTHONPATH
python mcp_inventory_server.py
```

### ポートが使用中の場合

MCPサーバーはSTDIOを使用するため、ポート競合は発生しません。

## ファイル構成

```
langflow-mcp/
├── mcp_inventory_server.py    # MCPサーバー本体
├── mcp_client.py               # テスト用クライアント
├── mcp_config.json             # Claude Desktop 設定例
├── MCP_SETUP.md                # このファイル
└── scmopt2/
    └── optinv.py               # 在庫最適化ロジック
```

## 次のステップ

1. FastAPI チャットアプリに OpenAI Function Calling を統合
2. MCP ツールを呼び出すエンドポイントを追加
3. フロントエンドでツール呼び出し結果を表示

---

**作成日:** 2025-10-05
**バージョン:** 1.0

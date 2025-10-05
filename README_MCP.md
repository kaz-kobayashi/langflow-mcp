# AIチャットエージェント × MCP 統合ガイド

## 概要

`03inventory.ipynb`のサプライチェーン在庫最適化機能をAIチャットエージェントから呼び出せるように統合しました。

## 実装内容

### 1. MCPサーバー（FastMCP）

**ファイル:** [mcp_inventory_server.py](mcp_inventory_server.py)

4つのツールを提供：
- `calculate_eoq`: 経済発注量計算
- `calculate_safety_stock`: 安全在庫レベル計算
- `optimize_safety_stock_allocation`: マルチエシュロン在庫最適化（MESSA）
- `analyze_inventory_network`: 在庫ネットワーク分析

### 2. OpenAI Function Calling 統合

**ファイル:**
- [mcp_tools.py](mcp_tools.py) - ツール定義と実行関数
- [main.py](main.py) - FastAPIバックエンド（Function Calling対応）
- [templates/index.html](templates/index.html) - フロントエンド（関数呼び出し結果表示）

### 3. アーキテクチャ

```
ユーザー
  ↓
[Frontend (Alpine.js)]
  ↓ HTTP POST /api/chat
[FastAPI Backend]
  ↓ OpenAI API (tools付き)
[OpenAI GPT]
  ↓ tool_calls
[mcp_tools.py]
  ↓ execute_mcp_function()
[scmopt2/optinv.py]
  ↓
結果を返す
```

## 使い方

### ローカル開発環境（Ollama使用時）

**注意:** Ollamaは`tools`パラメータをサポートしていないため、Function Callingは動作しません。

OpenAI APIを使用する場合は、`.env`を変更：

```bash
OPENAI_API_KEY=sk-your-actual-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 本番環境（Railway）

Railway の環境変数に以下を設定済み：

```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
SECRET_KEY=...
```

### チャット例

**ユーザー:** 発注固定費用が1000円、平均需要量が100個/日、在庫保管費用が1円/個/日、品切れ費用が100円/個/日の場合の経済発注量を計算してください。

**AI（Function Calling）:**
1. `calculate_eoq`関数を呼び出し
2. 結果を取得：
```json
{
  "optimal_order_quantity": 447.21,
  "total_cost": 447.21,
  "parameters": {...}
}
```
3. ユーザーに分かりやすく説明

## テスト方法

### 1. ローカルサーバー起動

```bash
python -m uvicorn main:app --reload --port 8000
```

### 2. ブラウザでアクセス

```
http://localhost:8000
```

1. ユーザー登録/ログイン
2. チャットで在庫最適化の質問
3. AIがFunction Callingを使って自動的にツールを呼び出す

### 3. Python スクリプトでテスト

```bash
python test_mcp_integration.py
```

## Claude Desktop での利用

**設定ファイル:** `~/.config/claude/claude_desktop_config.json`

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

Claude Desktop を再起動すると、チャット中にツールが利用可能になります。

## ファイル一覧

```
langflow-mcp/
├── mcp_inventory_server.py       # FastMCPサーバー
├── mcp_tools.py                   # OpenAI Function Calling用ツール定義
├── mcp_client.py                  # テスト用MCPクライアント
├── mcp_config.json                # Claude Desktop設定例
├── test_mcp_integration.py        # 統合テスト
├── main.py                        # FastAPIバックエンド（Function Calling対応）
├── templates/index.html           # フロントエンド（関数呼び出し結果表示）
├── MCP_SETUP.md                   # MCPセットアップガイド
└── README_MCP.md                  # このファイル
```

## トラブルシューティング

### 1. Function Callingが動作しない

**原因:** Ollamaは`tools`パラメータをサポートしていません。

**解決策:** `.env`でOpenAI APIを使用するように変更：

```bash
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 2. ModuleNotFoundError: No module named 'scmopt2'

**原因:** PYTHONPATHが設定されていません。

**解決策:**

```bash
export PYTHONPATH=/Users/kazuhiro/Documents/2510/langflow-mcp:$PYTHONPATH
python mcp_inventory_server.py
```

### 3. bcrypt エラー

Railway デプロイ時に発生する場合は、`requirements.txt`に以下が含まれているか確認：

```
bcrypt==4.0.1
```

## 次のステップ

1. ✅ MCPサーバー作成（FastMCP）
2. ✅ OpenAI Function Calling 統合
3. ✅ フロントエンド更新（関数呼び出し結果表示）
4. ⏳ OpenAI API キーで本番テスト
5. ⏳ 他のnotebook機能の追加（需要予測、ロットサイジングなど）

---

**作成日:** 2025-10-05
**バージョン:** 1.0

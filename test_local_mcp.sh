#!/bin/bash

# ローカルMCPテスト用スクリプト

echo "========================================="
echo "ローカル環境でMCPツールをテスト"
echo "========================================="
echo ""

# 1. FastAPIサーバーをバックグラウンドで起動
echo "1. FastAPIサーバーを起動中..."
cd /Users/kazuhiro/Documents/2510/langflow-mcp
python3 main.py > /tmp/fastapi_local.log 2>&1 &
FASTAPI_PID=$!
echo "   FastAPI起動完了 (PID: $FASTAPI_PID)"
echo "   ログ: /tmp/fastapi_local.log"
sleep 3

# 2. ユーザー登録してトークン取得
echo ""
echo "2. テストユーザーを登録中..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "local-test@example.com",
    "username": "localtest",
    "password": "testpass123"
  }')

TOKEN=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "   ❌ トークン取得失敗"
    echo "   レスポンス: $RESPONSE"
    kill $FASTAPI_PID
    exit 1
fi

echo "   ✅ トークン取得成功"
echo "   トークン: ${TOKEN:0:50}..."

# 3. Claude Desktop設定を更新
echo ""
echo "3. Claude Desktop設定を更新中..."

CLAUDE_CONFIG="/Users/kazuhiro/Library/Application Support/Claude/claude_desktop_config.json"

cat > "$CLAUDE_CONFIG" << EOF
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "/Users/kazuhiro/.pyenv/versions/3.12.3/bin/python3",
      "args": [
        "/Users/kazuhiro/Documents/2510/langflow-mcp/mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "$TOKEN",
        "INVENTORY_API_URL": "http://localhost:8000"
      }
    }
  }
}
EOF

echo "   ✅ 設定ファイル更新完了"

# 4. テスト実行
echo ""
echo "4. API接続テスト..."
TEST_RESULT=$(curl -s -X GET http://localhost:8000/api/tools \
  -H "Authorization: Bearer $TOKEN")

echo "   結果: $(echo $TEST_RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'{data.get(\"total\", 0)}個のツールが利用可能')" 2>/dev/null || echo "エラー")"

echo ""
echo "========================================="
echo "✅ セットアップ完了！"
echo "========================================="
echo ""
echo "次のステップ:"
echo "1. Claude Desktopを再起動:"
echo "   pkill -9 'Claude' && sleep 2 && open -a Claude"
echo ""
echo "2. Claude Desktopで試してください:"
echo "   「在庫最適化ツールの一覧を教えてください」"
echo ""
echo "3. テスト終了後、FastAPIサーバーを停止:"
echo "   kill $FASTAPI_PID"
echo ""
echo "FastAPI PID: $FASTAPI_PID"
echo "ログ: /tmp/fastapi_local.log"

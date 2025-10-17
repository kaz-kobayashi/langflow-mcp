#!/bin/bash

# セルフサービス登録スクリプト（同僚用）

echo "========================================="
echo "在庫最適化MCP - ユーザー登録"
echo "========================================="
echo ""

# ユーザー情報を入力
echo "あなたのアカウント情報を入力してください："
echo ""
read -p "メールアドレス: " EMAIL
read -p "ユーザー名: " USERNAME
read -sp "パスワード: " PASSWORD
echo ""
read -sp "パスワード（確認）: " PASSWORD_CONFIRM
echo ""

# パスワード確認
if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
    echo "❌ パスワードが一致しません"
    exit 1
fi

# 入力チェック
if [ -z "$EMAIL" ] || [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo "❌ すべてのフィールドを入力してください"
    exit 1
fi

echo ""
echo "📝 ユーザー登録中..."

# ユーザー登録
RESPONSE=$(curl -s -X POST https://web-production-1ed39.up.railway.app/api/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")

# トークンを抽出
TOKEN=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ ユーザー登録に失敗しました"
    ERROR=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('detail', 'Unknown error'))" 2>/dev/null)
    echo "エラー: $ERROR"
    exit 1
fi

echo "✅ ユーザー登録成功！"
echo ""
echo "========================================="
echo "【重要】APIトークン"
echo "========================================="
echo ""
echo "以下のトークンは大切に保管してください。"
echo "このトークンは7日間有効です。"
echo ""
echo "$TOKEN"
echo ""
echo "========================================="

# トークンをファイルに保存
TOKEN_FILE="$HOME/.inventory_mcp_token"
echo "$TOKEN" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"

echo ""
echo "✅ トークンを保存しました: $TOKEN_FILE"
echo ""

# 自動セットアップを提案
read -p "Claude Desktopの設定を自動で行いますか？ (y/n): " AUTO_SETUP

if [ "$AUTO_SETUP" = "y" ] || [ "$AUTO_SETUP" = "Y" ]; then
    # OSを検出
    if [[ "$OSTYPE" == "darwin"* ]]; then
        CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
        PYTHON_CMD="python3"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
        PYTHON_CMD="python3"
    else
        echo "⚠️  自動セットアップはmacOS/Linuxのみ対応しています"
        echo "Windows環境の場合は、README.mdの手順に従ってください"
        exit 0
    fi

    # Pythonパスを取得
    PYTHON_PATH=$(which $PYTHON_CMD)

    # MCPディレクトリの確認
    MCP_DIR="$HOME/inventory-mcp"
    if [ ! -f "$MCP_DIR/mcp_remote_server.py" ]; then
        echo "❌ $MCP_DIR/mcp_remote_server.py が見つかりません"
        echo "   配布パッケージを解凍してセットアップしてください"
        exit 1
    fi

    # Claude Desktop設定を作成
    mkdir -p "$CLAUDE_CONFIG_DIR"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

    cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "$PYTHON_PATH",
      "args": [
        "$MCP_DIR/mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "$TOKEN",
        "INVENTORY_API_URL": "https://web-production-1ed39.up.railway.app"
      }
    }
  }
}
EOF

    chmod 600 "$CLAUDE_CONFIG_FILE"

    echo "✅ Claude Desktop設定完了"
    echo ""
    echo "Claude Desktopを再起動してください："
    echo "  pkill -9 'Claude' && open -a Claude"
else
    echo ""
    echo "手動でセットアップする場合は、README.mdを参照してください。"
    echo "トークン: $TOKEN_FILE に保存されています"
fi

echo ""
echo "========================================="
echo ""
echo "【次のステップ】"
echo "1. Claude Desktopを再起動"
echo "2. 「利用可能な在庫最適化ツールの一覧を教えてください」と質問"
echo ""
echo "【トークン再発行（期限切れ時）】"
echo "curl -X POST https://web-production-1ed39.up.railway.app/api/login \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"email\":\"${EMAIL}\",\"password\":\"YOUR_PASSWORD\"}'"
echo ""
echo "========================================="

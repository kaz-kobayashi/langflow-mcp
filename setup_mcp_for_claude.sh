#!/bin/bash

# Claude Desktop用MCPサーバーセットアップスクリプト

echo "========================================="
echo "Claude Desktop MCP Server Setup"
echo "在庫最適化ツール"
echo "========================================="
echo ""

# 現在のディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 必要なパッケージをチェック
echo "📦 必要なパッケージをチェック中..."
if ! python3 -c "import fastmcp" 2>/dev/null; then
    echo "⚠️  fastmcpがインストールされていません"
    echo "インストール中..."
    pip install fastmcp requests
fi

echo "✓ パッケージOK"
echo ""

# トークンを環境変数から取得
if [ -z "$INVENTORY_API_TOKEN" ]; then
    echo "🔑 APIトークンが設定されていません"
    echo ""
    echo "トークンを取得するには、以下のいずれかを実行してください："
    echo ""
    echo "# 既存アカウントでログイン:"
    echo "curl -X POST https://web-production-1ed39.up.railway.app/api/login \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"email\":\"your-email@example.com\",\"password\":\"your-password\"}'"
    echo ""
    echo "# 新規登録:"
    echo "curl -X POST https://web-production-1ed39.up.railway.app/api/register \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"email\":\"your-email@example.com\",\"username\":\"username\",\"password\":\"password\"}'"
    echo ""
    echo "取得したトークンを入力してください:"
    read -r TOKEN

    if [ -z "$TOKEN" ]; then
        echo "❌ トークンが入力されませんでした"
        exit 1
    fi
else
    TOKEN="$INVENTORY_API_TOKEN"
    echo "✓ 環境変数からトークンを読み込みました"
fi

echo ""
echo "📝 Claude Desktop設定ファイルを作成中..."

# Claude Desktop設定ディレクトリを作成
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

mkdir -p "$CLAUDE_CONFIG_DIR"

# 既存の設定ファイルを確認
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "⚠️  既存の設定ファイルが見つかりました"
    echo "バックアップを作成します: ${CLAUDE_CONFIG_FILE}.backup"
    cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}.backup"
fi

# 新しい設定を作成
cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "python3",
      "args": [
        "${SCRIPT_DIR}/mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "${TOKEN}",
        "INVENTORY_API_URL": "https://web-production-1ed39.up.railway.app"
      }
    }
  }
}
EOF

# パーミッション設定
chmod 600 "$CLAUDE_CONFIG_FILE"

echo "✓ 設定ファイルを作成しました: $CLAUDE_CONFIG_FILE"
echo ""

# MCPサーバーのテスト
echo "🧪 MCPサーバーをテスト中..."
export INVENTORY_API_TOKEN="$TOKEN"

timeout 5 python3 "$SCRIPT_DIR/mcp_remote_server.py" 2>&1 | head -5 || true

echo ""
echo "========================================="
echo "✅ セットアップ完了！"
echo "========================================="
echo ""
echo "次のステップ:"
echo "1. Claude Desktopを再起動してください"
echo ""
echo "   macOS: "
echo "   pkill -9 'Claude' && open -a Claude"
echo ""
echo "2. Claude Desktopで以下のように質問してみてください:"
echo ""
echo "   「在庫最適化ツールで利用可能な機能を教えてください」"
echo ""
echo "   「年間需要15000個、発注コスト500円、保管費率25%、"
echo "    単価12円の場合のEOQを計算してください」"
echo ""
echo "========================================="
echo ""
echo "📚 詳細なドキュメント:"
echo "   - セットアップガイド: $SCRIPT_DIR/MCP_CLAUDE_DESKTOP_SETUP.md"
echo "   - API使用ガイド: $SCRIPT_DIR/API_USAGE_GUIDE.md"
echo ""

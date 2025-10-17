#!/bin/bash

# 同僚用：自動セットアップスクリプト
# このスクリプトを実行するだけでMCPサーバーがセットアップされます

echo "========================================="
echo "在庫最適化MCP - 自動セットアップ"
echo "========================================="
echo ""

# OSを検出
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    PYTHON_CMD="python3"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
    PYTHON_CMD="python3"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
    CLAUDE_CONFIG_DIR="$APPDATA/Claude"
    PYTHON_CMD="python"
else
    echo "❌ サポートされていないOSです: $OSTYPE"
    exit 1
fi

echo "検出されたOS: $OS"
echo ""

# ステップ1: Pythonの確認
echo "【ステップ1】Pythonの確認..."
PYTHON_PATH=$(which $PYTHON_CMD 2>/dev/null)

if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Pythonが見つかりません"
    echo "Python 3.8以上をインストールしてください"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "✅ Python確認完了: $PYTHON_VERSION"
echo "   パス: $PYTHON_PATH"
echo ""

# ステップ2: 必要なパッケージのインストール
echo "【ステップ2】必要なパッケージをインストール..."

if $PYTHON_CMD -c "import fastmcp" 2>/dev/null; then
    echo "✅ fastmcp: 既にインストール済み"
else
    echo "📦 fastmcpをインストール中..."
    $PYTHON_CMD -m pip install fastmcp
fi

if $PYTHON_CMD -c "import requests" 2>/dev/null; then
    echo "✅ requests: 既にインストール済み"
else
    echo "📦 requestsをインストール中..."
    $PYTHON_CMD -m pip install requests
fi

echo ""

# ステップ3: MCPディレクトリの作成
echo "【ステップ3】MCPディレクトリの作成..."
MCP_DIR="$HOME/inventory-mcp"
mkdir -p "$MCP_DIR"
echo "✅ ディレクトリ作成完了: $MCP_DIR"
echo ""

# ステップ4: 必要なファイルの確認
echo "【ステップ4】必要なファイルの確認..."

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$CURRENT_DIR/mcp_remote_server.py" ]; then
    echo "❌ mcp_remote_server.py が見つかりません"
    echo "   このスクリプトと同じディレクトリに配置してください"
    exit 1
fi

if [ ! -f "$CURRENT_DIR/inventory_client.py" ]; then
    echo "❌ inventory_client.py が見つかりません"
    echo "   このスクリプトと同じディレクトリに配置してください"
    exit 1
fi

# ファイルをコピー
cp "$CURRENT_DIR/mcp_remote_server.py" "$MCP_DIR/"
cp "$CURRENT_DIR/inventory_client.py" "$MCP_DIR/"

echo "✅ ファイルコピー完了"
echo ""

# ステップ5: APIトークンの入力
echo "【ステップ5】APIトークンの設定..."
echo ""
echo "管理者から受け取ったAPIトークンを入力してください。"
echo "（トークンを持っていない場合は、管理者に連絡してください）"
echo ""
read -p "APIトークン: " API_TOKEN

if [ -z "$API_TOKEN" ]; then
    echo "❌ トークンが入力されませんでした"
    exit 1
fi

echo ""

# ステップ6: Claude Desktop設定ファイルの作成
echo "【ステップ6】Claude Desktop設定を作成中..."

mkdir -p "$CLAUDE_CONFIG_DIR"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

# 既存の設定ファイルを確認
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "⚠️  既存の設定ファイルが見つかりました"
    echo "バックアップを作成します..."
    cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ バックアップ作成完了"
fi

# 新しい設定を作成
cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "$PYTHON_PATH",
      "args": [
        "$MCP_DIR/mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "$API_TOKEN",
        "INVENTORY_API_URL": "https://web-production-1ed39.up.railway.app"
      }
    }
  }
}
EOF

# パーミッション設定
chmod 600 "$CLAUDE_CONFIG_FILE"

echo "✅ 設定ファイル作成完了: $CLAUDE_CONFIG_FILE"
echo ""

# ステップ7: トークンのテスト
echo "【ステップ7】トークンをテスト中..."
TEST_RESULT=$(curl -s -X GET https://web-production-1ed39.up.railway.app/api/tools \
  -H "Authorization: Bearer $API_TOKEN" | $PYTHON_CMD -c "import sys, json; data=json.load(sys.stdin); print('OK' if 'tools' in data else 'NG')" 2>/dev/null)

if [ "$TEST_RESULT" = "OK" ]; then
    echo "✅ トークンは正常に動作しています"
else
    echo "⚠️  トークンのテストに失敗しました"
    echo "   トークンが正しいか確認してください"
fi

echo ""
echo "========================================="
echo "✅ セットアップ完了！"
echo "========================================="
echo ""
echo "【次のステップ】"
echo ""
echo "1. Claude Desktopを再起動してください"
echo ""

if [ "$OS" = "mac" ]; then
    echo "   macOS:"
    echo "   pkill -9 'Claude' && open -a Claude"
elif [ "$OS" = "linux" ]; then
    echo "   Linux:"
    echo "   killall claude-desktop && claude-desktop &"
else
    echo "   Windows:"
    echo "   タスクマネージャーからClaude Desktopを終了して再起動"
fi

echo ""
echo "2. Claude Desktopで以下のように質問してみてください："
echo ""
echo "   「利用可能な在庫最適化ツールの一覧を教えてください」"
echo ""
echo "   「年間需要15000個、発注コスト500円、保管費率25%、"
echo "    単価12円の場合のEOQを計算してください」"
echo ""
echo "========================================="
echo ""
echo "【トラブルシューティング】"
echo ""
echo "もしエラーが発生した場合："
echo "1. Claude Desktopのログを確認"
if [ "$OS" = "mac" ]; then
    echo "   ~/Library/Logs/Claude/mcp.log"
else
    echo "   %APPDATA%/Claude/Logs/mcp.log"
fi
echo ""
echo "2. 管理者に以下の情報を共有："
echo "   - Python: $PYTHON_VERSION"
echo "   - OS: $OS"
echo "   - エラーメッセージ"
echo ""
echo "========================================="

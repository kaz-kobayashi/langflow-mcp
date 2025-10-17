#!/bin/bash

# 同僚用トークン発行スクリプト

echo "========================================="
echo "在庫最適化MCP - 同僚用トークン発行"
echo "========================================="
echo ""

# ユーザー情報を入力
read -p "同僚のメールアドレス: " EMAIL
read -p "ユーザー名: " USERNAME
read -sp "パスワード: " PASSWORD
echo ""

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
    echo "レスポンス: $RESPONSE"
    exit 1
fi

echo "✅ ユーザー登録成功！"
echo ""
echo "========================================="
echo "以下の情報を同僚に共有してください"
echo "========================================="
echo ""
echo "【アカウント情報】"
echo "メールアドレス: $EMAIL"
echo "ユーザー名: $USERNAME"
echo "パスワード: $PASSWORD"
echo ""
echo "【APIトークン】（7日間有効）"
echo "$TOKEN"
echo ""
echo "【セットアップファイル】"
echo "以下のファイルを同僚に送付してください："
echo "  - mcp_remote_server.py"
echo "  - inventory_client.py"
echo "  - SETUP_FOR_COLLEAGUES.md（セットアップ手順）"
echo ""
echo "========================================="

# トークンをテスト
echo ""
echo "🧪 トークンをテスト中..."
TEST=$(curl -s -X GET https://web-production-1ed39.up.railway.app/api/tools \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print('OK' if 'tools' in data else 'NG')" 2>/dev/null)

if [ "$TEST" = "OK" ]; then
    echo "✅ トークンは正常に動作しています"
else
    echo "⚠️  トークンのテストに失敗しました"
fi

echo ""
echo "【トークン再発行方法】"
echo "トークンの有効期限が切れた場合、以下のコマンドで再発行できます："
echo ""
echo "curl -X POST https://web-production-1ed39.up.railway.app/api/login \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}'"
echo ""

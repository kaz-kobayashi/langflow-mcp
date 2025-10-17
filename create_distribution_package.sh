#!/bin/bash

# 配布用パッケージ作成スクリプト

echo "========================================="
echo "配布用パッケージ作成"
echo "========================================="
echo ""

PACKAGE_NAME="inventory-mcp-setup-$(date +%Y%m%d)"
PACKAGE_DIR="/tmp/$PACKAGE_NAME"

# 作業ディレクトリを作成
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

echo "📦 パッケージを作成中..."

# 必要なファイルをコピー
cp mcp_remote_server.py "$PACKAGE_DIR/"
cp inventory_client.py "$PACKAGE_DIR/"
cp setup_for_colleague.sh "$PACKAGE_DIR/"
cp self_register.sh "$PACKAGE_DIR/"
cp SETUP_FOR_COLLEAGUES_V3.md "$PACKAGE_DIR/README.md"

# README.txtを作成（簡易版）
cat > "$PACKAGE_DIR/README.txt" << 'EOF'
==========================================
在庫最適化MCP セットアップパッケージ
==========================================

【重要】
このパッケージは、Railway上の在庫最適化APIに接続するための
設定ファイルです。すべての計算処理はクラウド上で実行されます。

このパッケージには以下が含まれます：
- mcp_remote_server.py: MCP接続スクリプト（接続のみ担当）
- inventory_client.py: APIクライアント（接続のみ担当）
- self_register.sh: セルフサービス登録スクリプト（推奨）
- setup_for_colleague.sh: 手動セットアップスクリプト
- README.md: 詳細なセットアップガイド

【クイックスタート（推奨）】

新規ユーザーの場合:
  1. pip3 install fastmcp requests
  2. chmod +x self_register.sh
  3. ./self_register.sh
  4. Claude Desktopを再起動

既にWebアプリでアカウントを持っている場合:
  1. pip3 install fastmcp requests
  2. 以下のコマンドでトークンを取得:
     curl -X POST https://web-production-1ed39.up.railway.app/api/login \
       -H "Content-Type: application/json" \
       -d '{"email":"your-email","password":"your-password"}'
  3. README.mdの「既存アカウントでのセットアップ」を参照

動作確認:
  Claude Desktopで「利用可能な在庫最適化ツールの一覧を教えてください」
  と質問してください。

【仕組み】

Claude Desktop
  ↓ (MCP接続)
mcp_remote_server.py (ローカル・接続のみ)
  ↓ (HTTPS)
Railway FastAPI (クラウド・計算処理)

すべての在庫最適化計算はRailway上で実行されます。
ローカルのスクリプトは接続を仲介するだけです。

【サポート】

詳細な手順とトラブルシューティングは README.md を参照してください。

==========================================
EOF

# ZIPアーカイブを作成
cd /tmp
ZIP_FILE="${PACKAGE_NAME}.zip"
zip -r "$ZIP_FILE" "$PACKAGE_NAME" > /dev/null

# 元のディレクトリに移動
cd - > /dev/null

# ZIPファイルを現在のディレクトリにコピー
cp "/tmp/$ZIP_FILE" "./"

echo "✅ パッケージ作成完了！"
echo ""
echo "【配布ファイル】"
echo "  $ZIP_FILE"
echo ""
echo "【含まれるファイル】"
ls -lh "$PACKAGE_DIR"
echo ""
echo "【次のステップ】"
echo "1. $ZIP_FILE を同僚に送付"
echo "2. 同僚にAPIトークンを発行"
echo "   ./create_colleague_token.sh を実行"
echo ""
echo "【セットアップ手順（同僚向け）】"
echo "1. ZIPファイルを解凍"
echo "2. setup_for_colleague.sh を実行"
echo "3. APIトークンを入力"
echo "4. Claude Desktopを再起動"
echo ""
echo "========================================="
echo ""
echo "パッケージの場所:"
echo "$(pwd)/$ZIP_FILE"
echo ""

# クリーンアップ
rm -rf "$PACKAGE_DIR"

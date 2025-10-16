# Railway JWT認証エラーの修正方法

## 問題の概要

Railway上のAPIが全てのJWTトークンで "Not authenticated" エラーを返しています。
新規登録で生成されたトークンも認証に失敗しています。

## 原因

以下のいずれかの問題が考えられます：

1. **auth.pyの修正がデプロイされていない**
   - JWT payloadの "sub" (ユーザーID) を文字列から整数に変換する修正が必要

2. **JWT_SECRET_KEY環境変数の不整合**
   - トークン生成時と検証時で異なるシークレットキーが使用されている

## 修正手順

### ステップ1: Railway CLIでプロジェクトをリンク

```bash
cd /Users/kazuhiro/Documents/2510/langflow-mcp
railway link
```

プロンプトが表示されたら、プロジェクトを選択してください。

### ステップ2: 環境変数を確認

```bash
railway variables
```

以下の環境変数が設定されているか確認：
- `SECRET_KEY`: JWTトークンの署名に使用するシークレットキー（**重要**）
- `ADMIN_PASSWORD`: 管理画面用パスワード（設定済み）

**重要**: `SECRET_KEY` が設定されていない場合、デフォルト値が使用されます。
新規デプロイや再起動のたびに異なる値になる可能性があるため、必ず設定してください。

```bash
# シークレットキーを生成
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成されたキーをRailwayに設定
railway variables set SECRET_KEY="<generated-key>"
```

### ステップ3: 最新コードをデプロイ

```bash
# Gitでコミット（まだの場合）
git add auth.py main.py
git commit -m "Fix JWT authentication: convert user_id from string to int"
git push

# Railwayが自動的に再デプロイします
```

### ステップ4: デプロイ完了を確認

```bash
# デプロイログを確認
railway logs

# デプロイが完了するまで待つ（通常1-3分）
```

### ステップ5: 認証をテスト

```bash
# 新しいトークンを生成
curl -X POST https://web-production-1ed39.up.railway.app/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-fix@example.com",
    "username": "testfix",
    "password": "testpass123"
  }'

# 生成されたトークンをコピーして以下で使用
TOKEN="<your-token-here>"

# トークンをテスト
curl -X GET https://web-production-1ed39.up.railway.app/api/tools \
  -H "Authorization: Bearer $TOKEN"
```

成功すれば、ツール一覧が返ってきます。

## auth.pyの重要な修正箇所

Railway上の `auth.py` ファイルに以下の修正が必要です：

```python
# ❌ 修正前（バグ）
user_id: int = payload.get("sub")
user = db.query(User).filter(User.id == user_id).first()

# ✅ 修正後
user_id_str: str = payload.get("sub")
if user_id_str is None:
    raise credentials_exception
user_id = int(user_id_str)  # 文字列から整数に変換
user = db.query(User).filter(User.id == user_id).first()
```

この修正により、JWT payloadから取得した文字列のユーザーIDを整数に変換してからデータベースクエリに使用します。

## Claude DesktopのMCP設定

Railway認証が修正されたら、Claude Desktopを再起動してください：

```bash
# Claude Desktopを完全終了
pkill -9 "Claude"

# 再起動
open -a Claude
```

## トラブルシューティング

### エラー: "railway: command not found"

Railway CLIをインストール：

```bash
brew install railway
```

または：

```bash
npm install -g @railway/cli
```

### エラー: "No linked project found"

Railwayにログイン：

```bash
railway login
```

その後、プロジェクトをリンク：

```bash
railway link
```

### 認証がまだ失敗する場合

1. **ローカルでテスト**：
   ```bash
   # ローカルでAPIを起動
   python main.py

   # 別のターミナルでテスト
   curl -X POST http://localhost:8000/api/register ...
   ```

2. **SECRET_KEYを再設定**：
   ```bash
   # 新しいシークレットキーを生成
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"

   # Railwayに設定
   railway variables set SECRET_KEY="<generated-key>"
   ```

3. **Railwayのログを確認**：
   ```bash
   railway logs --tail
   ```

## MCPサーバーの動作確認

Railway認証が修正されたら、MCPサーバーも正常に動作するはずです。

ローカルでテスト：

```bash
export INVENTORY_API_TOKEN="<your-valid-token>"
export INVENTORY_API_URL="https://web-production-1ed39.up.railway.app"
python3 mcp_remote_server.py
```

Claude Desktop上で確認：
1. Claude Desktopを再起動
2. チャットで「在庫最適化ツールが使えるか確認してください」と入力
3. MCPツールが正常に表示されれば成功

## 連絡先

問題が解決しない場合は、以下の情報を共有してください：
- `railway logs` の出力
- `railway variables` の出力（シークレットキーは除く）
- テスト時のcurlコマンドとレスポンス

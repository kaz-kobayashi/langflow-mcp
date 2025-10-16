# JWTトークン発行ガイド

このガイドでは、在庫最適化APIを利用するためのJWTトークンを発行する方法を説明します。

---

## トークン発行方法一覧

1. **ユーザー自身が登録・ログイン**（セルフサービス） - 推奨
2. **管理者が代理で発行**（管理者向けスクリプト使用）

---

## 方法1: ユーザー自身が登録・ログイン（推奨）

### A. curlコマンドを使用

#### ステップ1: 新規登録

```bash
curl -X POST https://your-railway-app.railway.app/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "username": "your-username",
    "password": "your-secure-password"
  }'
```

**成功レスポンス**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

この `access_token` があなたのJWTトークンです。

#### ステップ2: トークンを保存

```bash
# 環境変数に保存（推奨）
export API_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# または安全なファイルに保存
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." > ~/.inventory_api_token
chmod 600 ~/.inventory_api_token
```

#### ステップ3: トークンを使用してAPIを呼び出す

```bash
curl -X POST https://your-railway-app.railway.app/api/tools/calculate_eoq_raw \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "annual_demand": 15000,
    "order_cost": 500.0,
    "holding_cost_rate": 0.25,
    "unit_price": 12.0
  }'
```

#### 既存ユーザーのログイン

すでにアカウントを持っている場合は、ログインしてトークンを取得できます。

```bash
curl -X POST https://your-railway-app.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

---

### B. Python SDKを使用

#### インストール

```bash
# inventory_client.py をダウンロード
wget https://your-railway-app.railway.app/inventory_client.py

# または直接コピー
# プロジェクトルートの inventory_client.py を使用
```

#### 使用例

```python
from inventory_client import InventoryOptimizationClient

# 新規登録
client = InventoryOptimizationClient(base_url="https://your-railway-app.railway.app")
token = client.register(
    email="your-email@example.com",
    username="your-username",
    password="your-secure-password"
)

print(f"あなたのトークン: {token}")

# トークンを保存
with open("my_api_token.txt", "w") as f:
    f.write(token)

# 既存ユーザーのログイン
# token = client.login(
#     email="your-email@example.com",
#     password="your-password"
# )
```

#### 保存したトークンを使用

```python
from inventory_client import InventoryOptimizationClient

# 保存したトークンを読み込み
with open("my_api_token.txt") as f:
    token = f.read().strip()

# トークンを使ってクライアントを初期化
client = InventoryOptimizationClient(
    base_url="https://your-railway-app.railway.app",
    token=token
)

# APIを使用
result = client.calculate_eoq(
    annual_demand=15000,
    order_cost=500.0,
    holding_cost_rate=0.25,
    unit_price=12.0
)
print(result)
```

---

### C. Webブラウザを使用（本番環境）

1. https://your-railway-app.railway.app/ にアクセス
2. 「新規登録」ボタンをクリック
3. メールアドレス、ユーザー名、パスワードを入力
4. 登録完了後、ブラウザの開発者ツール（F12）を開く
5. `localStorage.getItem('token')` でトークンを取得

---

## 方法2: 管理者がトークンを発行（管理者向け）

管理者専用のスクリプトを使用してユーザーアカウントとトークンを発行できます。

### 前提条件

- データベースへのアクセス権限
- `create_user_token.py` スクリプトへのアクセス

### A. コマンドラインモード

#### 新規ユーザー作成とトークン発行

```bash
python create_user_token.py \
  --email user@example.com \
  --username username \
  --password securepass123
```

**出力例**:
```
✅ ユーザー作成成功！

ユーザーID: 4
ユーザー名: username
メールアドレス: user@example.com

🔑 JWTトークン:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0IiwiZXhwIjoxNzYxMTMxMTAyfQ...

※このトークンは7日間有効です
※ユーザーにこのトークンを安全に共有してください
```

#### 既存ユーザーのトークン再発行

```bash
python create_user_token.py --email user@example.com --reissue
```

**出力例**:
```
✅ トークン再発行成功！

ユーザー: username (user@example.com)

🔑 新しいJWTトークン:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0IiwiZXhwIjoxNzYxMTMxMjY0fQ...

※このトークンは7日間有効です
```

#### 登録済みユーザー一覧表示

```bash
python create_user_token.py --list
```

**出力例**:
```
登録済みユーザー (3人):
--------------------------------------------------------------------------------
ID    Username             Email                          Created At
--------------------------------------------------------------------------------
1     kobayashi            kobayashi@moai-lab.jp          2025-10-04 21:52:48
2     testuser             test@example.com               2025-10-05 00:32:20
3     testapi              testapi@example.com            2025-10-15 10:21:48
--------------------------------------------------------------------------------
```

---

### B. 対話モード

```bash
python create_user_token.py
```

対話的にユーザー作成やトークン再発行ができます。

**メニュー**:
```
=== ユーザートークン管理 ===

1. 新規ユーザー作成とトークン発行
2. 既存ユーザーのトークン再発行
3. 登録済みユーザー一覧を表示
4. 終了

選択してください (1-4):
```

---

## トークンの管理

### トークンの有効期限

- **有効期間**: 7日間
- **期限切れ後**: 再ログインまたは再発行が必要

### トークンの安全な保管方法

#### ローカル開発環境

```bash
# 環境変数ファイルに保存
echo "INVENTORY_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." > .env

# .envファイルを.gitignoreに追加
echo ".env" >> .gitignore
```

#### プログラムから使用

```python
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("INVENTORY_API_TOKEN")
```

#### CI/CD環境

GitHub Actions、GitLab CI などでは、シークレット変数として保存します。

```yaml
# .github/workflows/example.yml
env:
  API_TOKEN: ${{ secrets.INVENTORY_API_TOKEN }}
```

---

## トークンを使用したAPI呼び出し例

### curl

```bash
export TOKEN="your-jwt-token-here"

# ツール一覧を取得
curl -X GET https://your-railway-app.railway.app/api/tools \
  -H "Authorization: Bearer $TOKEN"

# EOQ計算
curl -X POST https://your-railway-app.railway.app/api/tools/calculate_eoq_raw \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "annual_demand": 15000,
    "order_cost": 500.0,
    "holding_cost_rate": 0.25,
    "unit_price": 12.0
  }'
```

### Python

```python
import requests

TOKEN = "your-jwt-token-here"
BASE_URL = "https://your-railway-app.railway.app"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# EOQ計算
response = requests.post(
    f"{BASE_URL}/api/tools/calculate_eoq_raw",
    json={
        "annual_demand": 15000,
        "order_cost": 500.0,
        "holding_cost_rate": 0.25,
        "unit_price": 12.0
    },
    headers=headers
)

result = response.json()
print(f"最適発注量: {result['optimal_order_quantity']}")
```

### JavaScript (Node.js)

```javascript
const TOKEN = "your-jwt-token-here";
const BASE_URL = "https://your-railway-app.railway.app";

async function calculateEOQ() {
    const response = await fetch(`${BASE_URL}/api/tools/calculate_eoq_raw`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${TOKEN}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            annual_demand: 15000,
            order_cost: 500.0,
            holding_cost_rate: 0.25,
            unit_price: 12.0
        })
    });

    const result = await response.json();
    console.log(`最適発注量: ${result.optimal_order_quantity}`);
}

calculateEOQ();
```

---

## トラブルシューティング

### エラー: "Not authenticated"

**原因**: トークンが無効、期限切れ、または正しく送信されていない

**解決方法**:
1. トークンの有効期限を確認（7日間）
2. `Authorization: Bearer ` ヘッダーが正しいか確認
3. トークン文字列に余分なスペースや改行がないか確認
4. 再ログインしてトークンを再取得

### エラー: "Email already registered"

**原因**: 指定したメールアドレスが既に登録されている

**解決方法**:
- ログインエンドポイント (`/api/login`) を使用してトークンを取得
- または別のメールアドレスで登録

### エラー: "Username already taken"

**原因**: 指定したユーザー名が既に使用されている

**解決方法**:
- 別のユーザー名で登録

---

## セキュリティのベストプラクティス

1. **トークンを公開リポジトリにコミットしない**
   - `.gitignore` に追加
   - 環境変数または秘密管理システムを使用

2. **トークンをログに出力しない**
   - デバッグ時は注意

3. **HTTPSを使用**
   - 本番環境では必ずHTTPS経由でAPIを呼び出す

4. **定期的にトークンを更新**
   - 7日ごとに自動更新するスクリプトを検討

5. **アクセス権限を最小化**
   - 必要なツールだけにアクセスを制限（将来的な拡張）

---

## サポート

トークン発行に関する問題がある場合は、以下の情報を含めてお問い合わせください：

- 使用した発行方法（セルフサービス/管理者発行）
- エラーメッセージ（ある場合）
- 使用したコマンドまたはコード（トークンは含めないでください）

---

## 付録: トークンの構造

JWTトークンは以下の3つの部分で構成されています：

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0IiwiZXhwIjoxNzYxMTMxMTAyfQ.A7zeFEzSm5JhdXGEM9GM7agZ64xxGgDZsC5yb6euk_8
|                                       |                                     |
|       ヘッダー                        |          ペイロード                |       署名
```

- **ヘッダー**: アルゴリズム情報（HS256）
- **ペイロード**: ユーザーID、有効期限
- **署名**: 改ざん検知用

トークンをデコードしたい場合は https://jwt.io で確認できます（本番トークンは使用しないでください）。

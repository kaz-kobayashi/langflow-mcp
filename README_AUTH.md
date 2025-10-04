# 🤖 AI Chat Agent (認証付き)

FastAPI + Alpine.js + Tailwind CSSを使用したモダンなAIチャットアプリケーション。
JWT認証、ユーザー登録・ログイン機能付き。npm不要でCDN経由で動作します。

## ✨ 特徴

- 🚀 **npmなし** - 全てのフロントエンドライブラリはCDN経由で読み込み
- 💬 **リアルタイムストリーミング** - OpenAI互換APIでストリーミングレスポンス
- 🎨 **モダンUI** - Tailwind CSS + Alpine.jsによる美しいインターフェース
- 🔐 **JWT認証** - ユーザー登録・ログイン機能付き
- 💾 **チャット履歴保存** - データベースにユーザーごとの会話を保存
- 🔒 **セキュア** - パスワードハッシュ化、JWTトークン認証
- ☁️ **簡単デプロイ** - Render/Railway/Herokuに対応

## 🛠️ 技術スタック

### バックエンド
- FastAPI
- OpenAI Python SDK
- SQLAlchemy (ORM)
- PostgreSQL / SQLite
- JWT認証 (python-jose)
- パスワードハッシュ化 (passlib + bcrypt)

### フロントエンド (CDN)
- Alpine.js 3.x
- Tailwind CSS
- Vanilla JavaScript

## 📦 インストール

### 1. リポジトリをクローン

```bash
git clone <your-repo-url>
cd langflow-mcp
```

### 2. 仮想環境を作成

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 依存関係をインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数を設定

`.env`ファイルを編集：

```bash
# ローカルLLM（Ollama等）を使用する場合
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=not-needed

# OpenAI公式APIを使用する場合
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_API_KEY=sk-your-api-key-here

# JWT Secret Key (本番環境では必ず変更してください)
SECRET_KEY=your-secret-key-change-this-in-production
```

## 🚀 ローカルで実行

### 開発サーバーを起動

```bash
uvicorn main:app --reload
```

ブラウザで http://localhost:8000 を開く

## 🔐 認証フロー

1. **新規登録** (`/`) - メールアドレス、ユーザー名、パスワードで登録
2. **ログイン** (`/`) - メールアドレスとパスワードでログイン
3. **チャット** (`/chat`) - 認証済みユーザーのみアクセス可能
4. **ログアウト** - ヘッダーのログアウトボタンからログアウト

## 💾 データベース

### ローカル開発
- SQLiteを自動使用（`chat_app.db`）

### 本番環境
- PostgreSQLを推奨
- 環境変数 `DATABASE_URL` で設定

### モデル

- **User** - id, email, username, hashed_password, created_at
- **ChatHistory** - id, user_id, role, content, created_at

## ☁️ デプロイ

### Renderにデプロイ

1. [Render](https://render.com)でアカウント作成
2. GitHubリポジトリを接続
3. `render.yaml`が自動検出されます
4. 環境変数を設定：
   - `OPENAI_API_KEY`: あなたのOpenAI APIキー
   - `OPENAI_BASE_URL`: `https://api.openai.com/v1`
   - `SECRET_KEY`: ランダムな文字列（自動生成）
   - `DATABASE_URL`: PostgreSQL（自動設定）

### Railwayにデプロイ

1. [Railway](https://railway.app)でアカウント作成
2. "New Project" → "Deploy from GitHub repo"
3. PostgreSQLプラグインを追加
4. 環境変数を設定：
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `SECRET_KEY`
   - `DATABASE_URL` (PostgreSQLプラグインから自動設定)

## 📁 プロジェクト構成

```
langflow-mcp/
├── main.py              # FastAPIアプリケーション + 認証API
├── database.py          # SQLAlchemyモデル (User, ChatHistory)
├── auth.py              # JWT認証ユーティリティ
├── requirements.txt     # Python依存関係
├── templates/
│   ├── login.html      # ログイン・登録画面
│   └── index.html      # チャット画面（認証必須）
├── .env                # 環境変数
├── .gitignore
├── Procfile            # Heroku用
├── render.yaml         # Render用
└── README.md
```

## 🔧 カスタマイズ

### LLMモデルを変更

`templates/index.html`の以下の部分を編集：

```javascript
model: 'gpt-oss'  // ← ここを変更
```

### JWTトークン有効期限

`auth.py`の以下の部分を編集：

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7日間
```

### UIカラーテーマ

`templates/*.html`のTailwindクラスを編集してカスタマイズ可能です。

## 📝 API エンドポイント

### 認証
- `POST /api/register` - ユーザー登録
- `POST /api/login` - ログイン

### チャット
- `GET /` - ログイン画面
- `GET /chat` - チャット画面
- `POST /api/chat` - チャットメッセージ送信（認証必須、ストリーミング対応）

### その他
- `GET /health` - ヘルスチェック

## 🔒 セキュリティ

- パスワードは bcrypt でハッシュ化
- JWT トークンで認証
- SECRET_KEY は本番環境で必ず変更
- HTTPS 推奨（デプロイ先で自動設定）

## 🤝 貢献

プルリクエストを歓迎します！

## 📄 ライセンス

MIT

## 🔗 リンク

- [FastAPI](https://fastapi.tiangolo.com/)
- [Alpine.js](https://alpinejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [SQLAlchemy](https://www.sqlalchemy.org/)

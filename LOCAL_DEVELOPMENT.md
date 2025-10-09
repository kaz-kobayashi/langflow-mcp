# ローカル開発環境のセットアップ

## 前提条件

1. **Ollamaのインストール**
   ```bash
   # macOSの場合
   brew install ollama

   # または公式サイトからダウンロード
   # https://ollama.ai/
   ```

2. **gpt-oss:latestモデルのプル**
   ```bash
   ollama pull gpt-oss:latest
   ```

3. **Python環境**
   ```bash
   pip install -r requirements.txt
   ```

## ローカル開発の開始

### 1. Ollamaサーバーの起動

別のターミナルでOllamaサーバーを起動します：

```bash
ollama serve
```

### 2. アプリケーションの起動

```bash
./run_local.sh
```

このスクリプトは以下を自動的に行います：
- `.env.local`を`.env`にコピー
- Ollamaの起動確認
- gpt-oss:latestモデルの存在確認
- FastAPIサーバーの起動（ポート8000）

### 3. 動作確認

ブラウザで以下にアクセス：
- API: http://localhost:8000
- ドキュメント: http://localhost:8000/docs
- MCPツール一覧: http://localhost:8000/mcp/tools

## 開発ワークフロー

### コードの変更

1. **ローカルで開発**
   ```bash
   # ローカルサーバーを起動
   ./run_local.sh

   # コードを編集
   # FastAPIは--reloadオプションで自動リロード
   ```

2. **テストの実行**
   ```bash
   # 特定のPhaseのテスト
   python test_phase11_1.py
   python test_phase11_2.py
   python test_phase11_3.py

   # 全テスト
   pytest test_phase*.py -v
   ```

3. **コミット**
   ```bash
   git add .
   git commit -m "機能追加の説明"
   ```

### 本番環境へのデプロイ

開発が完了したら、デプロイスクリプトを実行：

```bash
./deploy.sh
```

このスクリプトは以下を自動的に行います：
- .envが本番用設定か確認
- テストの実行
- Git push（Railwayが自動デプロイ）

## 環境変数の管理

### ローカル開発用（.env.local）

```bash
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=not-needed
OPENAI_MODEL_NAME=gpt-oss:latest
SECRET_KEY=local-development-secret-key
ENVIRONMENT=local
```

### 本番環境用（.env）

```bash
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_MODEL_NAME=gpt-4
SECRET_KEY=production-secret-key
ENVIRONMENT=production
```

**重要**: `.env`は本番用設定のまま保持し、ローカル開発時は`run_local.sh`で自動的に`.env.local`から上書きされます。

## トラブルシューティング

### Ollamaに接続できない

```bash
# Ollamaが起動しているか確認
curl http://localhost:11434/api/tags

# 起動していない場合
ollama serve
```

### gpt-oss:latestモデルがない

```bash
# モデルをプル
ollama pull gpt-oss:latest

# 利用可能なモデルを確認
ollama list
```

### ポート8000が使用中

```bash
# 使用中のプロセスを確認
lsof -i :8000

# プロセスを終了
kill -9 <PID>
```

## 注意事項

1. **Function Callingの制限**
   - Ollamaのgpt-ossモデルはFunction Calling機能が制限される可能性があります
   - 完全なテストは本番環境（OpenAI API）で行うことを推奨

2. **パフォーマンス**
   - ローカルLLMは応答速度が遅い場合があります
   - 本番環境のパフォーマンスとは異なることに注意

3. **Git管理**
   - `.env`は.gitignoreに含まれています
   - `.env.local`もコミットしないでください（機密情報を含む場合）

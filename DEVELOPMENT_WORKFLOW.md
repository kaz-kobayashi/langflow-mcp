# 開発ワークフロー

このドキュメントでは、ローカル開発からデプロイまでの効率的なワークフローを説明します。

---

## 基本方針

1. **ローカル開発**: Ollama (gpt-oss:latest) でデバッグ・テスト
2. **テスト完了後**: Gitにコミット・プッシュ
3. **自動デプロイ**: Railway が自動的に本番環境にデプロイ

---

## 1. ローカル開発環境のセットアップ

### 1.1 Ollama のインストール

```bash
# macOS
brew install ollama

# または公式サイトからダウンロード
# https://ollama.ai/download
```

### 1.2 モデルのダウンロード

```bash
# Ollamaサーバーを起動
ollama serve

# 別のターミナルでモデルをプル
ollama pull gpt-oss:latest
```

### 1.3 環境設定の確認

`.env.local`ファイルが存在することを確認：

```bash
cat .env.local
```

内容：
```bash
# Ollama Configuration for Local Development
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=not-needed
OPENAI_MODEL_NAME=gpt-oss:latest

# JWT Secret Key
SECRET_KEY=local-development-secret-key-do-not-use-in-production

# Environment
ENVIRONMENT=local
```

---

## 2. ローカル開発サーバーの起動

### 2.1 自動起動スクリプトを使用

```bash
./run_local.sh
```

このスクリプトは以下を自動で行います：
1. Ollamaの起動確認
2. gpt-oss:latestモデルの存在確認
3. `.env.local`を`.env`にコピー
4. FastAPIサーバーを起動（ポート8000）

### 2.2 手動起動（デバッグ用）

```bash
# 環境変数を設定
cp .env.local .env

# サーバー起動
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2.3 アクセス

- **WebUI**: http://localhost:8000
- **API**: http://localhost:8000/api/chat
- **Health Check**: http://localhost:8000/health
- **Docs**: http://localhost:8000/docs

---

## 3. テスト実行

### 3.1 自動テストスクリプト

```bash
# ローカル環境でテスト
python test_comprehensive_auto.py

# 特定の範囲をテスト
python test_comprehensive_auto.py --start 1 --end 10
```

### 3.2 個別のPhaseテスト

```bash
# Phase 13-1: 動的計画法
python test_phase13_1.py

# Phase 13-2: 分布ベースシミュレーション
python test_phase13_2.py

# Phase 12-1: ネットワークベースストック
python test_phase12_1.py

# Phase 12-2: シミュレーション軌道可視化
python test_phase12_2.py

# キャッシュ機構
python test_cache_mechanism.py
```

### 3.3 手動テスト（WebUI）

1. http://localhost:8000 を開く
2. COMPREHENSIVE_TEST_EXAMPLES.mdから入力例をコピー
3. チャット欄に貼り付けて実行
4. 結果を確認

---

## 4. デバッグ方法

### 4.1 ログの確認

FastAPIサーバーのターミナルでリアルタイムログを確認：

```
INFO:     127.0.0.1:50123 - "POST /api/chat HTTP/1.1" 200 OK
```

### 4.2 エラーのトレース

エラーが発生した場合、サーバーログに詳細なトレースバックが表示されます：

```python
# 例
Traceback (most recent call last):
  File "mcp_tools.py", line 1234, in execute_mcp_function
    ...
```

### 4.3 コードの変更

`--reload`オプションが有効なため、ファイルを変更すると自動的にサーバーが再起動されます：

```bash
# ファイルを編集
vim mcp_tools.py

# 保存すると自動的に再起動
INFO:     Will watch for changes in these directories: ['/Users/kazuhiro/Documents/2510/langflow-mcp']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
```

### 4.4 ブレークポイントの使用

```python
# コードにブレークポイントを挿入
import pdb; pdb.set_trace()

# または
breakpoint()
```

実行時にデバッガーが起動します。

---

## 5. コミットとデプロイ

### 5.1 変更のテスト完了後

```bash
# 変更内容を確認
git status
git diff

# ステージング
git add .

# コミット
git commit -m "Description of changes"

# プッシュ
git push origin main
```

### 5.2 Railway での自動デプロイ

GitHubにプッシュすると、Railwayが自動的に：

1. 変更を検知
2. 新しいビルドを開始
3. テストを実行（設定されている場合）
4. 本番環境にデプロイ

デプロイ状況の確認：
- Railwayダッシュボード: https://railway.app
- デプロイログを確認

### 5.3 本番環境での動作確認

```bash
# 本番環境でテスト
python test_comprehensive_auto.py --url https://web-production-1ed39.up.railway.app/api/chat

# 範囲指定
python test_comprehensive_auto.py \
  --url https://web-production-1ed39.up.railway.app/api/chat \
  --start 1 --end 5
```

---

## 6. トラブルシューティング

### 6.1 Ollama が起動しない

```bash
# Ollamaプロセスを確認
ps aux | grep ollama

# 手動で起動
ollama serve

# 別のターミナルで確認
curl http://localhost:11434/api/tags
```

### 6.2 gpt-oss:latest が見つからない

```bash
# モデルのリストを確認
ollama list

# gpt-oss:latestがない場合はプル
ollama pull gpt-oss:latest
```

### 6.3 ポート8000が使用中

```bash
# プロセスを確認
lsof -i :8000

# プロセスを終了
kill -9 <PID>

# または別のポートを使用
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 6.4 モジュールが見つからない

```bash
# 依存関係を再インストール
pip install -r requirements.txt

# または個別にインストール
pip install <module-name>
```

### 6.5 可視化が表示されない

可視化ファイルの保存先を確認：

```bash
# デフォルトは /tmp/visualizations
ls /tmp/visualizations

# または環境変数で変更
export VISUALIZATION_OUTPUT_DIR=/path/to/visualizations
```

---

## 7. ベストプラクティス

### 7.1 開発の流れ

1. **機能追加・修正**
   - ローカル環境で実装
   - `./run_local.sh` で起動
   - WebUIで動作確認

2. **テスト**
   - 自動テストスクリプトで確認
   - エラーがあれば修正
   - すべてのテストが通過するまで繰り返し

3. **コミット**
   - 意味のあるコミットメッセージを書く
   - 関連する変更をまとめる
   - 大きな変更は小さく分割

4. **プッシュ**
   - `git push` で本番環境に反映
   - Railwayのログを確認
   - 本番環境でも動作確認

### 7.2 コミットメッセージの例

```bash
# 良い例
git commit -m "Add visualization for safety stock allocation

新機能:
- optimize_safety_stock_allocationに可視化機能を追加
- visualization_idを結果に含める

修正:
- Plotly colorbarのtitlesideプロパティを修正

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 悪い例
git commit -m "fix bug"
git commit -m "update"
```

### 7.3 ブランチ戦略（オプション）

大きな機能追加の場合：

```bash
# フィーチャーブランチを作成
git checkout -b feature/new-mcp-tool

# 開発・コミット
git add .
git commit -m "Add new MCP tool"

# mainブランチに戻る
git checkout main

# マージ
git merge feature/new-mcp-tool

# ブランチを削除
git branch -d feature/new-mcp-tool
```

---

## 8. 開発環境と本番環境の違い

| 項目 | ローカル開発 | Railway本番環境 |
|------|------------|-----------------|
| **LLMモデル** | Ollama (gpt-oss:latest) | OpenAI API (gpt-4) |
| **API URL** | http://localhost:8000 | https://web-production-1ed39.up.railway.app |
| **環境変数** | `.env.local` | Railway設定 |
| **可視化保存先** | `/tmp/visualizations` | Railway永続ストレージ |
| **デバッグ** | `--reload`モードで即座に反映 | プッシュ後に自動デプロイ |
| **コスト** | 無料（ローカルリソース） | OpenAI API課金 |

---

## 9. 便利なコマンド集

### 9.1 開発

```bash
# ローカルサーバー起動
./run_local.sh

# ログをファイルに保存
./run_local.sh 2>&1 | tee server.log

# バックグラウンドで起動
nohup ./run_local.sh > server.log 2>&1 &

# プロセス確認
ps aux | grep uvicorn

# 停止
pkill -f uvicorn
```

### 9.2 テスト

```bash
# 全テスト実行
python test_comprehensive_auto.py

# 詳細出力
python test_comprehensive_auto.py --verbose

# 結果を別ファイルに保存
python test_comprehensive_auto.py --output my_test_results.txt

# 本番環境でテスト
python test_comprehensive_auto.py \
  --url https://web-production-1ed39.up.railway.app/api/chat \
  --output prod_test_results.txt
```

### 9.3 Git

```bash
# 最近のコミットを確認
git log --oneline -10

# 特定ファイルの変更履歴
git log -p mcp_tools.py

# 差分を確認
git diff
git diff --staged

# 特定のコミットに戻る
git checkout <commit-hash>

# 元に戻す
git checkout main
```

---

## 10. まとめ

このワークフローに従うことで：

✅ **効率的な開発**: ローカルで素早くデバッグ
✅ **コスト削減**: Ollamaで無料開発
✅ **品質保証**: テスト完了後のみデプロイ
✅ **自動化**: Railwayで自動デプロイ

---

**関連ドキュメント**:
- [README.md](./README.md): プロジェクト概要
- [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md): ローカル開発環境の詳細
- [MCP_TOOLS_API_REFERENCE.md](./MCP_TOOLS_API_REFERENCE.md): API仕様
- [COMPREHENSIVE_TEST_EXAMPLES.md](./COMPREHENSIVE_TEST_EXAMPLES.md): テスト入力例

---

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*

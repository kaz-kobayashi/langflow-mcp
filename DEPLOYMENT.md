# デプロイメントガイド

## ローカルテスト

### 前提条件

- Python 3.10+
- OpenAI API キー（Function Calling を使う場合）

### 手順

#### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

#### 2. 環境変数の設定

`.env` ファイルを作成：

```bash
cp .env.example .env
```

`.env` を編集：

```bash
# OpenAI API を使う場合（Function Calling 対応）
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-actual-api-key

# JWT Secret Key
SECRET_KEY=your-random-secret-key
```

**注意:** Ollama は `tools` パラメータをサポートしていないため、Function Calling は動作しません。

#### 3. サーバー起動

```bash
python -m uvicorn main:app --reload --port 8000
```

#### 4. ブラウザでアクセス

```
http://localhost:8000
```

1. ユーザー登録/ログイン
2. チャットで質問

**テスト用の質問例:**

- 「発注固定費用が1000円、平均需要量が100個/日、在庫保管費用が1円/個/日、品切れ費用が100円/個/日の場合の経済発注量を計算してください」
- 「平均需要量が100個/日、標準偏差が10、リードタイムが3日、品切れ費用が100円/個/日、在庫保管費用が1円/個/日の場合の安全在庫を計算してください」

AIが自動的に `calculate_eoq` や `calculate_safety_stock` 関数を呼び出します。

---

## Railway へのデプロイ

### 前提条件

- GitHub アカウント
- Railway アカウント
- OpenAI API キー

### 手順

#### 1. GitHubにコミット＆プッシュ

```bash
git add .
git commit -m "Add MCP integration for supply chain optimization"
git push origin main
```

#### 2. Railway で環境変数を設定

**Railway Dashboard** → **langflow-mcp** → **web** → **Variables** タブ

以下の環境変数を追加：

```bash
OPENAI_API_KEY=sk-your-actual-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
SECRET_KEY=qWbtwSWDtDoMXoDvcfQ1aJCYYljCNkdyBfO1sYGzXg2V1MpHaGbudacLR9tZ3Twr_UpZxLKulNpR-BXMmeJSig
```

**注意:** `DATABASE_URL` は PostgreSQL プラグインが自動設定します。

#### 3. 自動デプロイ

Railway が GitHub の変更を検知して自動的にデプロイします。

#### 4. デプロイログの確認

**Deploy Logs** タブで以下を確認：

- ✅ 依存関係のインストール成功
- ✅ アプリケーション起動成功
- ❌ エラーがないか

#### 5. 動作確認

デプロイされたURL（例: `https://web-production-1ed39.up.railway.app`）にアクセス：

1. ユーザー登録
2. ログイン
3. チャットで在庫最適化の質問
4. Function Calling が動作するか確認

---

## トラブルシューティング

### 1. Function Calling が動作しない

**症状:** AIがツールを呼び出さず、通常の応答のみ

**原因と解決策:**

- ❌ Ollama を使用している → OpenAI API に切り替え
- ❌ `OPENAI_BASE_URL` が間違っている → `https://api.openai.com/v1` に設定
- ❌ `OPENAI_API_KEY` が無効 → 有効なキーを設定

### 2. ModuleNotFoundError

**症状:** `ModuleNotFoundError: No module named 'scmopt2'`

**解決策:**

ローカル:
```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
python main.py
```

Railway: `scmopt2/` ディレクトリがリポジトリに含まれているか確認

### 3. bcrypt エラー

**症状:** `error reading bcrypt version`

**解決策:** `requirements.txt` に `bcrypt==4.0.1` が含まれているか確認

### 4. PostgreSQL 接続エラー

**症状:** `could not connect to server`

**解決策:** Railway で PostgreSQL プラグインを追加

---

## 新しいMCPツールの追加方法

### 1. `mcp_tools.py` にツール定義を追加

```python
{
    "type": "function",
    "function": {
        "name": "new_tool_name",
        "description": "ツールの説明",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "number", "description": "パラメータ1"}
            },
            "required": ["param1"]
        }
    }
}
```

### 2. `execute_mcp_function` に実装を追加

```python
elif function_name == "new_tool_name":
    result = your_optimization_function(arguments["param1"])
    return {"result": result}
```

### 3. テストとデプロイ

```bash
# ローカルテスト
python -m uvicorn main:app --reload

# デプロイ
git add mcp_tools.py
git commit -m "Add new MCP tool"
git push
```

---

**更新日:** 2025-10-05

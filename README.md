# Inventory Optimization MCP Server

FastAPI + MCP (Model Context Protocol) ベースの在庫最適化・サプライチェーン管理システム

**最終更新**: 2025-10-09 | **Phase 13完了**

---

## 📋 概要

このプロジェクトは、在庫管理とサプライチェーン最適化のための包括的なMCPツール群を提供します。34個のMCPツールを通じて、以下の機能を利用できます：

- **在庫最適化**: 安全在庫配置、基在庫レベル計算、動的計画法
- **シミュレーション**: 多段階在庫、ネットワークベースストック、分布ベースシミュレーション
- **発注方策**: (Q,R)、(s,S)、基在庫方策の最適化とシミュレーション
- **需要予測**: 指数平滑法、移動平均法、分布フィッティング
- **EOQ計算**: 基本EOQ、数量割引対応EOQ
- **可視化**: サプライチェーンネットワーク、シミュレーション結果、最適化過程

---

## ✨ 主な機能

### Phase 13 (最新)
- **動的計画法による安全在庫配置** (Phase 13-1)
  - ツリー構造ネットワークに対する厳密解
  - Graves & Willems (2003) アルゴリズム実装

- **分布ベースの基在庫シミュレーション** (Phase 13-2)
  - 6種類の確率分布に対応（正規、一様、指数、ポアソン、ガンマ、対数正規）
  - 柔軟な需要モデリング

### Phase 12
- ネットワークベースストックシミュレーション
- シミュレーション軌道可視化
- シミュレーション結果のキャッシュ機構

### Phase 11
- サプライチェーンネットワーク可視化
- ヒストグラム分布フィッティング
- 多段階在庫シミュレーション

### Phase 10
- LR Finder（最適学習率探索）
- ワンサイクルLR法

### Phase 9
- EOQ計算（基本・増分数量割引・全単位数量割引）
- EOQ可視化

### Phase 7
- 定期発注最適化（Adam、SGD、Momentum対応）

### Phase 6
- 需要予測（指数平滑法、移動平均法）

---

## 🚀 クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/kaz-kobayashi/langflow-mcp.git
cd langflow-mcp
```

### 2. 仮想環境の作成

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env`ファイルを作成：

```bash
# OpenAI APIを使用する場合
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL_NAME=gpt-4

# JWT Secret Key
SECRET_KEY=your-secret-key-here

# Environment
ENVIRONMENT=production
```

---

## 💻 使い方

### ローカル開発環境での起動

```bash
# Ollamaを使用したローカル開発
./run_local.sh

# または手動起動
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

ブラウザで http://localhost:8000 を開く

### 本番環境での起動

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 📦 デプロイ

### Railwayへのデプロイ（推奨）

1. [Railway](https://railway.app)でアカウント作成
2. GitHubリポジトリを接続
3. 環境変数を設定:
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `OPENAI_MODEL_NAME`
   - `SECRET_KEY`
   - `ENVIRONMENT=production`

GitHub pushで自動デプロイが開始されます。

### Renderへのデプロイ

1. [Render](https://render.com)でアカウント作成
2. "New Web Service"を選択
3. GitHubリポジトリを接続
4. 環境変数を設定

`render.yaml`が自動的に使用されます。

---

## 📚 ドキュメント

### 主要ドキュメント

- **[MCP_TOOLS_API_REFERENCE.md](./MCP_TOOLS_API_REFERENCE.md)**: 全34個のMCPツールのAPI仕様
- **[PHASE13_SUMMARY.md](./PHASE13_SUMMARY.md)**: Phase 13実装の詳細サマリー
- **[PHASE13_INPUT_EXAMPLES.md](./PHASE13_INPUT_EXAMPLES.md)**: Phase 13の動作確認用入力例
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)**: Phase 12実装サマリー
- **[LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md)**: ローカル開発環境のセットアップガイド

### テストコード

- `test_phase13_1.py`: 動的計画法のテスト（5テスト）
- `test_phase13_2.py`: 分布ベースシミュレーションのテスト（7テスト）
- `test_phase12_1.py`: ネットワークベースストックのテスト（4テスト）
- `test_phase12_2.py`: シミュレーション軌道可視化のテスト（6テスト）
- `test_cache_mechanism.py`: キャッシュ機構のテスト（3テスト）

---

## 🛠️ プロジェクト構造

```
langflow-mcp/
├── main.py                          # FastAPIアプリケーション
├── mcp_tools.py                     # 34個のMCPツール実装
├── mcp_inventory_server.py          # MCPサーバー（非推奨）
├── optinv.py                        # 在庫最適化アルゴリズム（非推奨）
├── scmopt2/                         # メインアルゴリズムパッケージ
│   ├── optinv.py                    # 在庫最適化関数（35関数）
│   └── core.py                      # SCMGraph等のコアクラス
├── nbs/                             # Jupyter Notebook（元実装）
│   └── 03inventory.ipynb
├── templates/
│   └── index.html                   # WebUIフロントエンド
├── tests/
│   ├── test_phase13_1.py
│   ├── test_phase13_2.py
│   ├── test_phase12_1.py
│   ├── test_phase12_2.py
│   └── test_cache_mechanism.py
├── docs/
│   ├── MCP_TOOLS_API_REFERENCE.md
│   ├── PHASE13_SUMMARY.md
│   ├── PHASE13_INPUT_EXAMPLES.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── LOCAL_DEVELOPMENT.md
├── .env                             # 環境変数
├── .env.local                       # ローカル開発用環境変数
├── requirements.txt                 # Python依存パッケージ
├── run_local.sh                     # ローカル起動スクリプト
├── deploy.sh                        # デプロイスクリプト
└── README.md
```

---

## 🔧 カスタマイズ

### 新しいMCPツールの追加

`mcp_tools.py`の`execute_mcp_function`関数に新しいツールを追加：

```python
elif function_name == "your_new_tool":
    """
    ツールの説明
    """
    try:
        # ツールの実装
        return {
            "status": "success",
            # 出力データ
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
```

### LLMモデルの変更

`.env`ファイルで`OPENAI_MODEL_NAME`を変更：

```bash
OPENAI_MODEL_NAME=gpt-4-turbo
# または
OPENAI_MODEL_NAME=gpt-3.5-turbo
```

### ローカルLLMの使用

Ollama、LM Studio、llama.cpp等のローカルLLMを使用する場合：

```bash
# .env.local
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=not-needed
OPENAI_MODEL_NAME=gpt-oss:latest
```

---

## 📊 統計情報

### 実装完成度
- **全体**: 約98%完了
- **MCPツール**: 34個実装済み
- **テストカバレッジ**: 25テストケース、100%合格率

### コード統計
- **mcp_tools.py**: 約4,100行
- **scmopt2/optinv.py**: 35関数実装
- **テストコード**: 約1,400行
- **ドキュメント**: 約5,000行

---

## 🔌 API エンドポイント

### REST API

- `GET /` - WebUIの表示
- `POST /api/chat` - チャットメッセージの送信
- `POST /api/execute_mcp` - MCPツールの直接実行
- `GET /health` - ヘルスチェック
- `GET /api/visualizations/{viz_id}` - 可視化結果の取得

### MCP Tools

34個のMCPツールが利用可能。詳細は[API Reference](./MCP_TOOLS_API_REFERENCE.md)を参照。

---

## 🧪 テスト

### 全テストの実行

```bash
# Phase 13-1
python test_phase13_1.py

# Phase 13-2
python test_phase13_2.py

# Phase 12
python test_phase12_1.py
python test_phase12_2.py

# キャッシュ機構
python test_cache_mechanism.py
```

### 個別テストの実行

```bash
pytest test_phase13_1.py -v
```

---

## 🤝 コントリビューション

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

---

## 📄 ライセンス

MIT License

---

## 🙏 謝辞

このプロジェクトは以下の研究・ライブラリに基づいています：

- **Graves & Willems (2003)**: "Supply Chain Design: Safety Stock Placement and Supply Chain Configuration"
- **NetworkX**: グラフ理論とネットワーク分析
- **SciPy**: 科学計算とヒートマップ最適化
- **Plotly**: インタラクティブ可視化
- **FastAPI**: 高速Webフレームワーク

---

## 📞 連絡先

- **GitHub**: [kaz-kobayashi/langflow-mcp](https://github.com/kaz-kobayashi/langflow-mcp)
- **Issues**: [GitHub Issues](https://github.com/kaz-kobayashi/langflow-mcp/issues)

---

## 🗺️ ロードマップ

### 完了済み
- ✅ Phase 1-13: 全ての高・中優先度機能
- ✅ 34個のMCPツール
- ✅ キャッシュ機構
- ✅ ローカル開発環境
- ✅ 包括的なドキュメント

### 今後の拡張可能性
- 📊 Phase 13の可視化機能拡張
- 🔄 マルチオブジェクティブ最適化
- 📈 感度分析機能
- 🌐 多言語対応
- 📱 モバイルUI対応

---

**Built with ❤️ using FastAPI, NetworkX, SciPy, and Plotly**

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*

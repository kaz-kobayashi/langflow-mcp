# Claude DesktopでMCPサーバーを使用する設定ガイド

このガイドでは、Railway上のFastAPI在庫最適化ツールをClaude Desktopで使用する方法を説明します。

---

## 前提条件

1. **Claude Desktop**がインストールされていること
2. **Python 3.8+**がインストールされていること
3. **APIトークン**を取得済みであること

---

## ステップ1: 必要なパッケージをインストール

```bash
cd /Users/kazuhiro/Documents/2510/langflow-mcp
pip install fastmcp requests
```

---

## ステップ2: APIトークンを取得

### 方法A: 既存のアカウントでログイン

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

### 方法B: 新規登録

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "username": "your-username",
    "password": "your-password"
  }'
```

レスポンスから`access_token`をコピーしてください。

---

## ステップ3: 環境変数を設定

```bash
# トークンを環境変数に設定（一時的）
export INVENTORY_API_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 永続的に設定する場合は ~/.zshrc または ~/.bash_profile に追加
echo 'export INVENTORY_API_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."' >> ~/.zshrc
source ~/.zshrc
```

---

## ステップ4: Claude Desktopの設定ファイルを編集

### macOSの場合

```bash
# 設定ファイルの場所
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

設定ファイルが存在しない場合は新規作成してください：

```bash
mkdir -p ~/Library/Application\ Support/Claude
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Windowsの場合

```
%APPDATA%\Claude\claude_desktop_config.json
```

---

## ステップ5: MCPサーバーを設定ファイルに追加

`claude_desktop_config.json`を以下のように編集：

```json
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "python",
      "args": [
        "/Users/kazuhiro/Documents/2510/langflow-mcp/mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "あなたのJWTトークンをここに貼り付け",
        "INVENTORY_API_URL": "https://web-production-1ed39.up.railway.app"
      }
    }
  }
}
```

**重要**:
- `INVENTORY_API_TOKEN`の値を実際のJWTトークンに置き換えてください
- パスは絶対パスで指定してください

### 複数のMCPサーバーがある場合

既に他のMCPサーバーが設定されている場合は、カンマで区切って追加してください：

```json
{
  "mcpServers": {
    "existing-server": {
      "command": "...",
      "args": ["..."]
    },
    "inventory-optimizer": {
      "command": "python",
      "args": [
        "/Users/kazuhiro/Documents/2510/langflow-mcp/mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "あなたのJWTトークンをここに貼り付け",
        "INVENTORY_API_URL": "https://web-production-1ed39.up.railway.app"
      }
    }
  }
}
```

---

## ステップ6: Claude Desktopを再起動

設定を反映させるため、Claude Desktopを完全に終了して再起動してください。

macOSの場合：
```bash
# Claude Desktopを終了
pkill -9 "Claude"

# 再起動
open -a Claude
```

---

## ステップ7: 動作確認

Claude Desktopを開き、以下のようなプロンプトを試してください：

### 例1: 利用可能なツールを確認
```
在庫最適化で利用可能なツールを教えてください
```

### 例2: EOQ計算
```
年間需要15000個、発注コスト500円、保管費率25%、単価12円の場合の経済発注量を計算してください
```

### 例3: 安全在庫計算
```
平均需要100個/日、標準偏差20、リードタイム7日、サービスレベル95%の場合の安全在庫を計算してください
```

### 例4: (Q,R)方策の最適化
```
以下のパラメータで(Q,R)方策を最適化してください：
- 平均需要: 100個/日
- 標準偏差: 20
- リードタイム: 7日
- 在庫保管費用: 0.5円/個/日
- 品切れ費用: 50円/個
- 固定発注費用: 1000円/回
```

---

## トラブルシューティング

### エラー: "INVENTORY_API_TOKEN環境変数が設定されていません"

**原因**: トークンが設定されていない

**解決方法**:
1. `claude_desktop_config.json`の`env`セクションに正しいトークンを設定
2. Claude Desktopを再起動

### エラー: "Connection refused" または "API呼び出しに失敗"

**原因**: トークンが無効または期限切れ

**解決方法**:
1. 新しいトークンを取得（ステップ2を参照）
2. `claude_desktop_config.json`のトークンを更新
3. Claude Desktopを再起動

### エラー: "Module not found: fastmcp"

**原因**: 必要なパッケージがインストールされていない

**解決方法**:
```bash
pip install fastmcp requests
```

### MCPサーバーが表示されない

**原因**: 設定ファイルのJSON形式が間違っている

**解決方法**:
1. `claude_desktop_config.json`のJSON形式を確認
2. オンラインJSON validatorで検証: https://jsonlint.com/
3. Claude Desktopを再起動

---

## セキュリティに関する注意

1. **トークンを安全に管理**:
   - 設定ファイルのパーミッションを制限
   ```bash
   chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **トークンの有効期限**:
   - JWTトークンは7日間有効
   - 期限切れの場合は再ログインが必要

3. **トークンを共有しない**:
   - GitHubなどにコミットしない
   - スクリーンショットに含めない

---

## 利用可能なツール一覧

MCPサーバーを通じて以下のツールが利用可能です：

### EOQ計算
- `calculate_eoq` - 基本EOQ計算
- `calculate_eoq_with_discount` - 数量割引対応EOQ

### 安全在庫
- `calculate_safety_stock` - 安全在庫計算

### 在庫方策
- `optimize_qr_policy` - (Q,R)方策の最適化
- `simulate_qr_policy` - (Q,R)方策のシミュレーション
- `optimize_ss_policy` - (s,S)方策の最適化

### 需要予測・分析
- `forecast_demand` - 需要予測
- `analyze_demand_pattern` - 需要パターン分析
- `find_best_distribution` - 最適確率分布フィッティング

### その他
- `list_available_tools` - 利用可能なツール一覧を取得

---

## サポート

問題が発生した場合は、以下の情報を含めてお問い合わせください：

- Claude Desktopのバージョン
- エラーメッセージ（あれば）
- 使用したプロンプト
- `claude_desktop_config.json`の内容（トークンは除く）

---

## 次のステップ

MCPサーバーが正常に動作したら：

1. **より高度な分析**: 複数のツールを組み合わせて使用
2. **可視化**: `visualize=true`パラメータで結果を可視化
3. **自動化**: Claude Desktopを使って定期的な在庫分析を実行

詳細は`API_USAGE_GUIDE.md`を参照してください。

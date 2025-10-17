# 同僚向け：在庫最適化MCPサーバーのセットアップガイド

このガイドでは、Railway上の在庫最適化APIをClaude Desktopから使用する方法を説明します。

---

## 前提条件

- **Claude Desktop**がインストールされていること
- **Python 3.8以上**がインストールされていること
- インターネット接続

---

## セットアップ手順

### ステップ1: 必要なファイルを取得

以下の2つのファイルをダウンロードしてください：

1. `mcp_remote_server.py` - MCPサーバースクリプト
2. `inventory_client.py` - APIクライアント

**ダウンロード方法**：

```bash
# 任意のディレクトリで実行
mkdir -p ~/inventory-mcp
cd ~/inventory-mcp

# GitHubまたは共有フォルダからファイルをダウンロード
# 例:
# curl -O https://your-repo/mcp_remote_server.py
# curl -O https://your-repo/inventory_client.py
```

または、管理者からこれらのファイルを受け取ってください。

---

### ステップ2: 必要なPythonパッケージをインストール

```bash
pip install fastmcp requests
```

または、Python 3のバージョンを明示的に指定：

```bash
pip3 install fastmcp requests
```

---

### ステップ3: APIトークンを取得

管理者に連絡して、あなた専用のAPIトークンを発行してもらってください。

または、セルフサービスで登録：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "username": "your-username",
    "password": "your-secure-password"
  }'
```

レスポンスに含まれる `access_token` をコピーしてください。

---

### ステップ4: Claude Desktop設定ファイルを作成

#### macOSの場合

```bash
# 設定ディレクトリを作成
mkdir -p ~/Library/Application\ Support/Claude

# 設定ファイルを編集
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Windowsの場合

```powershell
# 設定ディレクトリを作成
New-Item -Path "$env:APPDATA\Claude" -ItemType Directory -Force

# 設定ファイルを編集
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

---

### ステップ5: 設定内容を記入

以下の内容を `claude_desktop_config.json` に貼り付けてください：

#### macOSの場合

```json
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "python3",
      "args": [
        "/Users/YOUR-USERNAME/inventory-mcp/mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "YOUR-JWT-TOKEN-HERE",
        "INVENTORY_API_URL": "https://web-production-1ed39.up.railway.app"
      }
    }
  }
}
```

#### Windowsの場合

```json
{
  "mcpServers": {
    "inventory-optimizer": {
      "command": "python",
      "args": [
        "C:\\Users\\YOUR-USERNAME\\inventory-mcp\\mcp_remote_server.py"
      ],
      "env": {
        "INVENTORY_API_TOKEN": "YOUR-JWT-TOKEN-HERE",
        "INVENTORY_API_URL": "https://web-production-1ed39.up.railway.app"
      }
    }
  }
}
```

**重要**：
- `YOUR-USERNAME` を実際のユーザー名に置き換えてください
- `YOUR-JWT-TOKEN-HERE` をステップ3で取得したトークンに置き換えてください
- パスは**絶対パス**で指定してください

---

### ステップ6: Python実行ファイルのパスを確認

Pythonが正しくインストールされているか確認：

```bash
# macOS/Linux
which python3

# Windows
where python
```

もし、`python3`が見つからない場合は、設定ファイルの `"command"` を修正してください：

```json
"command": "/usr/local/bin/python3"  // 実際のパスを指定
```

---

### ステップ7: Claude Desktopを再起動

#### macOS

```bash
pkill -9 "Claude"
open -a Claude
```

#### Windows

タスクマネージャーから Claude Desktop を終了して、再度起動してください。

---

### ステップ8: 動作確認

Claude Desktopを開き、以下のように質問してください：

```
利用可能な在庫最適化ツールの一覧を教えてください
```

成功すれば、34個のツールが表示されます。

---

## 簡単テスト例

### EOQ計算

```
年間需要15000個、発注コスト500円、保管費率25%、単価12円の場合の経済発注量を計算してください
```

### 安全在庫計算

```
平均需要100個/日、標準偏差20、リードタイム7日、サービスレベル95%の場合の安全在庫を計算してください
```

### (Q,R)方策の最適化

```
以下のパラメータで(Q,R)方策を最適化してください：
- 平均需要：100個/日
- 標準偏差：20
- リードタイム：7日
- 在庫保管費用：0.5円/個/日
- 品切れ費用：50円/個
- 固定発注費用：1000円/回
```

---

## トラブルシューティング

### エラー: "Could not attach to MCP server"

**原因1**: Pythonパスが間違っている

**解決方法**:
```bash
# 正しいPythonパスを確認
which python3  # macOS/Linux
where python   # Windows

# 設定ファイルのcommandフィールドを更新
```

**原因2**: fastmcpがインストールされていない

**解決方法**:
```bash
pip3 install fastmcp requests
```

---

### エラー: "401 Client Error: Unauthorized"

**原因**: トークンが無効または期限切れ

**解決方法**:
1. 新しいトークンを取得（管理者に依頼、または再登録）
2. `claude_desktop_config.json` のトークンを更新
3. Claude Desktopを再起動

---

### エラー: "Module not found: fastmcp"

**原因**: fastmcpが使用しているPythonにインストールされていない

**解決方法**:
```bash
# 設定ファイルで指定したPythonで直接インストール
/path/to/python3 -m pip install fastmcp requests
```

---

### MCPサーバーがリストに表示されない

**原因**: JSONファイルの形式が間違っている

**解決方法**:
1. https://jsonlint.com/ でJSON形式を検証
2. カンマやクォートの位置を確認
3. 既に他のMCPサーバーがある場合は、カンマで区切って追加

```json
{
  "mcpServers": {
    "existing-server": {
      "command": "...",
      "args": [...]
    },
    "inventory-optimizer": {
      "command": "python3",
      "args": [...]
    }
  }
}
```

---

## 利用可能な機能

このMCPサーバーでは、以下の34種類の在庫最適化ツールが利用できます：

### EOQ（経済発注量）
- 基本EOQ計算
- 数量割引対応EOQ（全単位・増分）
- EOQ可視化

### 安全在庫
- サービスレベルベース
- コストベース
- マルチエシュロン最適化（MESSA）

### 在庫方策
- (Q,R)方策の最適化・シミュレーション
- (s,S)方策の最適化・シミュレーション
- ベースストック方策
- 定期発注方式の最適化
- Wagner-Whitinアルゴリズム

### 需要予測・分析
- 移動平均法
- 指数平滑法
- 線形トレンド法
- 需要パターン分析
- 確率分布フィッティング

### 可視化
- EOQ分析グラフ
- 在庫シミュレーション
- サプライチェーンネットワーク図
- 需要予測グラフ
- コスト比較チャート

詳細は Claude Desktop で「在庫最適化ツールの一覧を教えてください」と質問してください。

---

## セキュリティに関する注意

1. **トークンを安全に管理**
   - 設定ファイルは他人と共有しない
   - GitHubなどにコミットしない
   - スクリーンショットに含めない

2. **トークンの有効期限**
   - JWTトークンは7日間有効
   - 期限切れの場合は再ログインが必要

3. **ファイルのパーミッション**
   ```bash
   # macOS/Linux
   chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

---

## サポート

問題が発生した場合は、以下の情報を添えて管理者に連絡してください：

- 使用しているOS（macOS/Windows/Linux）
- Claude Desktopのバージョン
- エラーメッセージ（あれば）
- MCPログファイル（`~/Library/Logs/Claude/mcp.log` または `%APPDATA%\Claude\Logs\mcp.log`）

---

## よくある質問

### Q: 複数のPCで同じトークンを使えますか？

A: はい、可能です。ただし、セキュリティの観点から、PC毎に異なるアカウントを作成することを推奨します。

### Q: トークンの有効期限は？

A: 発行から7日間です。期限切れになったら再ログインが必要です。

### Q: オフラインで使えますか？

A: いいえ、Railway上のAPIに接続する必要があるため、インターネット接続が必要です。

### Q: ツールの使い方がわかりません

A: Claude Desktopで自然に日本語で質問してください。Claudeが適切なツールを選択して実行します。

---

## 更新履歴

- 2025-10-16: 初版作成
- Railway本番環境（https://web-production-1ed39.up.railway.app）への接続設定

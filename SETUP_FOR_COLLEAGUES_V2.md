# 同僚向け：在庫最適化MCPサーバーのセットアップガイド

このガイドでは、Railway上の在庫最適化APIをClaude Desktopから使用する方法を説明します。

---

## 前提条件

- **Claude Desktop**がインストールされていること
- **Python 3.8以上**がインストールされていること
- インターネット接続

---

## 📦 クイックスタート（推奨）

**最も簡単な方法** - 自動セットアップスクリプトを使用

### ステップ1: 配布パッケージを解凍

管理者から受け取った `inventory-mcp-setup-YYYYMMDD.zip` を解凍してください。

```bash
unzip inventory-mcp-setup-YYYYMMDD.zip
cd inventory-mcp-setup-YYYYMMDD
```

### ステップ2: Pythonパッケージをインストール

```bash
pip3 install fastmcp requests
```

### ステップ3: セルフサービス登録スクリプトを実行

```bash
chmod +x self_register.sh
./self_register.sh
```

スクリプトが以下を自動的に行います：
1. アカウント作成
2. APIトークン生成
3. Claude Desktop設定（オプション）

**入力が必要な情報**：
- メールアドレス（あなたのメール）
- ユーザー名（任意）
- パスワード（自分で決める）

### ステップ4: Claude Desktopを再起動

```bash
pkill -9 'Claude' && open -a Claude
```

### ステップ5: 動作確認

Claude Desktopで質問してみてください：

```
利用可能な在庫最適化ツールの一覧を教えてください
```

34個のツールが表示されれば成功です！

---

## 🔧 手動セットアップ（管理者からトークンを受け取った場合）

管理者から以下の情報を受け取っている場合はこちら：

<details>
<summary>手動セットアップ手順を表示</summary>

### ステップ1: 必要なファイルの配置

配布パッケージを解凍：

```bash
unzip inventory-mcp-setup-YYYYMMDD.zip
mkdir -p ~/inventory-mcp
cp inventory-mcp-setup-YYYYMMDD/*.py ~/inventory-mcp/
```

### ステップ2: Pythonパッケージをインストール

```bash
pip3 install fastmcp requests
```

### ステップ3: Claude Desktop設定ファイルを作成

#### macOSの場合

```bash
mkdir -p ~/Library/Application\ Support/Claude
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

以下を貼り付け：

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

**重要**：
- `YOUR-USERNAME` を実際のユーザー名に置き換え
- `YOUR-JWT-TOKEN-HERE` を管理者から受け取ったトークンに置き換え

### ステップ4: Pythonパスを確認

```bash
which python3
```

もし `/usr/bin/python3` でない場合は、設定ファイルの `"command"` を実際のパスに変更してください。

### ステップ5: Claude Desktopを再起動

```bash
pkill -9 "Claude"
open -a Claude
```

</details>

---

## 💡 使い方の例

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

## 🔄 トークンの再発行（期限切れ時）

トークンは7日間有効です。期限が切れた場合：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

レスポンスから `access_token` をコピーして、Claude Desktop設定ファイルを更新し、再起動してください。

---

## ❓ トラブルシューティング

<details>
<summary>エラー: "Could not attach to MCP server"</summary>

**原因**: Pythonパスまたはfastmcpの問題

**解決方法**:

1. Pythonパスを確認：
   ```bash
   which python3
   ```

2. fastmcpをインストール：
   ```bash
   pip3 install fastmcp requests
   ```

3. 設定ファイルの `command` を確認
</details>

<details>
<summary>エラー: "401 Client Error: Unauthorized"</summary>

**原因**: トークンが無効または期限切れ

**解決方法**:

1. トークンを再発行（上記参照）
2. Claude Desktop設定ファイルを更新
3. Claude Desktopを再起動
</details>

<details>
<summary>エラー: "Module not found: fastmcp"</summary>

**原因**: 使用しているPythonにfastmcpがインストールされていない

**解決方法**:

```bash
# 設定ファイルで指定したPythonで直接インストール
/path/to/python3 -m pip install fastmcp requests
```
</details>

<details>
<summary>MCPサーバーがリストに表示されない</summary>

**原因**: JSON形式のエラー

**解決方法**:

1. https://jsonlint.com/ でJSON形式を検証
2. カンマやクォートの位置を確認
3. Claude Desktopを再起動
</details>

---

## 📋 利用可能な機能（34ツール）

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

---

## 🔒 セキュリティに関する注意

1. **パスワード管理**
   - 自分で決めたパスワードは安全に管理
   - 他人と共有しない

2. **トークン管理**
   - 設定ファイルは他人と共有しない
   - GitHubなどにコミットしない

3. **ファイルのパーミッション**
   ```bash
   chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

---

## 💬 よくある質問

**Q: 複数のPCで使えますか？**
A: はい、各PCで同じアカウントでログインできます。

**Q: トークンの有効期限は？**
A: 7日間です。期限が切れたら再ログインしてください。

**Q: オフラインで使えますか？**
A: いいえ、インターネット接続が必要です。

**Q: ツールの使い方がわかりません**
A: Claude Desktopで日本語で自然に質問してください。Claudeが適切なツールを選択します。

---

## 📞 サポート

問題が発生した場合は、以下の情報を添えて管理者に連絡してください：

- OS（macOS/Windows/Linux）
- エラーメッセージ
- MCPログ（`~/Library/Logs/Claude/mcp.log`）

---

## 更新履歴

- 2025-10-16: セルフサービス登録機能を追加
- Railway本番環境への接続設定

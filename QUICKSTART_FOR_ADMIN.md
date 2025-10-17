# 管理者向けクイックスタートガイド

同僚にRailway上の在庫最適化API（MCP接続）を使えるようにする配布手順です。

**重要**: すべての計算処理はRailway上で実行されます。同僚のPCには接続設定のみを配布します。

---

## 📦 ステップ1: 配布パッケージを作成

```bash
cd /Users/kazuhiro/Documents/2510/langflow-mcp
./create_distribution_package.sh
```

これで `inventory-mcp-setup-YYYYMMDD.zip` が作成されます。

---

## 🔑 ステップ2: 同僚用のAPIトークンを発行

```bash
./create_colleague_token.sh
```

以下の情報を入力：
- メールアドレス
- ユーザー名
- パスワード

スクリプトが自動的にトークンを生成し、表示します。

---

## 📧 ステップ3: 同僚に以下を送付

**推奨方法（セルフサービス）**: ZIPファイルのみを送付

1. **配布パッケージ（ZIPファイル）**
   - `inventory-mcp-setup-YYYYMMDD.zip`（接続設定ファイルのみ含む）

2. **セットアップ手順**（簡単版）
   ```
   1. ZIPファイルを解凍
   2. ターミナルを開いて解凍したフォルダに移動
   3. 以下を実行:
      pip3 install fastmcp requests
      chmod +x self_register.sh
      ./self_register.sh
   4. 自分のアカウント情報を入力（メール、ユーザー名、パスワード）
   5. Claude Desktopを再起動
   ```

**代替方法**: 管理者がトークンを発行して共有する場合は、`create_colleague_token.sh`を使用してください。

---

## 📝 送付メールのテンプレート

```
件名: Claude Desktop用 在庫最適化API接続セットアップ

お疲れ様です。

Claude Desktop上で在庫最適化ツール（34種類）を使えるように
Railway API接続用のセットアップファイルをお送りします。

【重要】
すべての計算処理はRailway（クラウド）上で実行されます。
PCには接続設定ファイルのみを配置します。

【添付ファイル】
- inventory-mcp-setup-YYYYMMDD.zip（接続設定ファイル）

【セットアップ手順】

■ 新規ユーザーの場合:

1. 添付のZIPファイルを解凍

2. ターミナルを開いて解凍したフォルダに移動

3. 以下のコマンドを実行：

   pip3 install fastmcp requests
   chmod +x self_register.sh
   ./self_register.sh

4. 自分のアカウント情報を入力：
   - メールアドレス
   - ユーザー名
   - パスワード

5. Claude Desktopを再起動

■ 既にWebアプリでアカウントを持っている場合:

1. ZIPファイルを解凍

2. pip3 install fastmcp requests

3. 既存のメールアドレスとパスワードでログイン:
   curl -X POST https://web-production-1ed39.up.railway.app/api/login \
     -H "Content-Type: application/json" \
     -d '{"email":"your-email","password":"your-password"}'

4. README.mdの「既存アカウントでのセットアップ」を参照して
   Claude Desktop設定を作成

5. Claude Desktopを再起動

【動作確認】

Claude Desktopで以下のように質問してみてください：

「利用可能な在庫最適化ツールの一覧を教えてください」

34個のツールが表示されれば成功です。

【アーキテクチャ】

Claude Desktop
  ↓ (MCP接続)
接続スクリプト（PC上・接続のみ）
  ↓ (HTTPS)
Railway API（クラウド・計算処理）

【トラブルシューティング】

詳細な手順やエラー対処法は、ZIPファイル内のREADME.mdを
ご参照ください。

問題が発生した場合はお気軽にご連絡ください。

よろしくお願いします。
```

---

## 🔄 トークン再発行（有効期限切れ時）

同僚のトークンが期限切れになった場合、以下のコマンドで再発行：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "colleague@example.com",
    "password": "their-password"
  }'
```

または、`create_colleague_token.sh` で新しいアカウントを作成。

---

## 📊 利用状況の確認

現在登録されているユーザーを確認：

```bash
python create_user_token.py --list
```

---

## 🛠️ トラブルシューティング（よくある問題）

### 同僚が「401 Unauthorized」エラー

**原因**: トークンが無効または期限切れ

**解決策**:
1. トークンを再発行
2. 同僚に新しいトークンを送付
3. Claude Desktop設定を更新して再起動

### 同僚が「Module not found: fastmcp」エラー

**原因**: fastmcpがインストールされていない

**解決策**:
```bash
pip3 install fastmcp requests
```

### 同僚のMCPサーバーが起動しない

**原因**: Pythonパスが間違っている

**解決策**:
1. `which python3` でパスを確認
2. Claude Desktop設定の`command`フィールドを更新

---

## 📚 参考ドキュメント

- `SETUP_FOR_COLLEAGUES_V3.md` - 詳細なセットアップガイド（同僚向け・リモートAPI接続のみ）
- `TOKEN_ISSUANCE_GUIDE.md` - トークン発行の詳細
- `MCP_CLAUDE_DESKTOP_SETUP.md` - MCPサーバー設定の詳細
- `API_USAGE_GUIDE.md` - API使用方法

---

## 🎯 配布チェックリスト

- [ ] 配布パッケージ（ZIP）を作成
- [ ] 同僚用トークンを発行
- [ ] アカウント情報をメモ
- [ ] ZIPファイルとアカウント情報を送付
- [ ] セットアップ手順を共有
- [ ] 動作確認の方法を伝達
- [ ] トラブルシューティング連絡先を共有

---

## 📞 サポート

同僚からの問い合わせ対応時に必要な情報：
- OS（macOS/Windows/Linux）
- Pythonバージョン
- エラーメッセージ
- MCPログファイル（`~/Library/Logs/Claude/mcp.log`）

これらの情報があれば、迅速にトラブルシューティングできます。

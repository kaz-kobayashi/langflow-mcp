# FastAPI アプリケーション 機能仕様書

## 目次
1. [はじめに](#はじめに)
2. [アーキテクチャ概要](#アーキテクチャ概要)
3. [データベースモデル](#データベースモデル)
4. [認証・セキュリティ](#認証セキュリティ)
5. [FastAPIエンドポイント](#fastapiエンドポイント)
6. [MCP Tools（在庫最適化ツール）](#mcp-tools在庫最適化ツール)
7. [SCRM Tools（サプライチェーンリスク管理ツール）](#scrm-toolsサプライチェーンリスク管理ツール)
8. [環境変数](#環境変数)

---

## はじめに

本アプリケーションは、**在庫最適化専門のAIチャットボット**です。FastAPI + OpenAI Function Calling + MCP（Model Context Protocol）Toolsを組み合わせて、ユーザーと対話しながら在庫最適化計算を実行します。

### 主な機能
- ユーザー認証（JWT）
- チャット履歴の保存
- OpenAI Function Callingによる自動ツール呼び出し
- **58種類**のサプライチェーン最適化・リスク管理機能
  - 在庫最適化ツール（43種類）: EOQ、安全在庫、定期発注、需要予測、ロットサイズ最適化、Excel連携、最適化結果の可視化など
  - サプライチェーンリスク管理ツール（6種類）: MERIODAS によるリスク分析
  - ロジスティクス・ネットワーク設計ツール（9種類）: MELOS による倉庫配置最適化、顧客集約、ネットワーク生成、可視化など
- インタラクティブな可視化（Plotly）

---

## アーキテクチャ概要

```
┌─────────────┐
│  Frontend   │ (HTML/JavaScript + Jinja2 Templates)
└──────┬──────┘
       │ HTTP/SSE
┌──────▼──────────────────────────────────────────┐
│              FastAPI Server                      │
│  ┌────────────────────────────────────────────┐ │
│  │  API Endpoints                             │ │
│  │  - /api/chat (Streaming + Function Call)  │ │
│  │  - /api/register, /api/login              │ │
│  │  - /api/visualization/{viz_id}            │ │
│  └───────────┬────────────────────────────────┘ │
│              │                                   │
│  ┌───────────▼───────────┐  ┌──────────────────┐│
│  │   OpenAI Client       │  │   MCP Tools      ││
│  │  (Function Calling)   │─▶│  (30+ functions) ││
│  └───────────────────────┘  └──────────────────┘│
│              │                                   │
│  ┌───────────▼───────────┐                      │
│  │   SQLAlchemy ORM      │                      │
│  │   (User, ChatHistory) │                      │
│  └───────────┬───────────┘                      │
└──────────────┼──────────────────────────────────┘
               │
     ┌─────────▼─────────┐
     │  PostgreSQL / SQLite │
     └───────────────────┘
```

---

## データベースモデル

### User モデル
**ファイル**: `database.py:17-26`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | Integer | プライマリキー |
| email | String | メールアドレス（ユニーク・インデックス） |
| username | String | ユーザー名（ユニーク・インデックス） |
| hashed_password | String | bcryptハッシュ化パスワード |
| created_at | DateTime | 作成日時（UTC） |
| chat_histories | Relationship | ChatHistoryテーブルとのリレーション |

**リレーション**: 1対多（User → ChatHistory）

---

### ChatHistory モデル
**ファイル**: `database.py:28-37`

| フィールド | 型 | 説明 |
|-----------|-----|------|
| id | Integer | プライマリキー |
| user_id | Integer | 外部キー（users.id） |
| role | String | メッセージの役割（"user" または "assistant"） |
| content | Text | メッセージ本文 |
| created_at | DateTime | 作成日時（UTC） |
| user | Relationship | Userテーブルとのリレーション |

---

### データベース関数

#### `init_db()`
**ファイル**: `database.py:40-41`

**機能**: データベーステーブルを作成（マイグレーション）

**入力**: なし

**出力**: なし

**使用例**:
```python
init_db()  # アプリ起動時に実行
```

---

#### `get_db()`
**ファイル**: `database.py:44-49`

**機能**: データベースセッションを生成（FastAPI Dependency）

**入力**: なし

**出力**: `Generator[Session]` - SQLAlchemyセッション

**使用例**:
```python
@app.post("/api/example")
async def example(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"users": users}
```

---

## 認証・セキュリティ

### 認証方式
- **JWT（JSON Web Token）** - HS256アルゴリズム
- **トークン有効期限**: 7日間
- **パスワードハッシュ**: bcrypt

---

### 認証関数

#### `get_password_hash(password: str) -> str`
**ファイル**: `auth.py:22-23`

**機能**: パスワードをbcryptでハッシュ化

**入力**:
- `password` (str): 平文パスワード

**出力**:
- `str`: bcryptハッシュ

**使用例**:
```python
hashed = get_password_hash("mypassword123")
# "$2b$12$..."
```

---

#### `verify_password(plain_password: str, hashed_password: str) -> bool`
**ファイル**: `auth.py:19-20`

**機能**: パスワードを検証

**入力**:
- `plain_password` (str): 平文パスワード
- `hashed_password` (str): ハッシュ化パスワード

**出力**:
- `bool`: 一致したらTrue

**使用例**:
```python
is_valid = verify_password("mypassword123", hashed)
# True
```

---

#### `create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str`
**ファイル**: `auth.py:25-33`

**機能**: JWTアクセストークンを生成

**入力**:
- `data` (dict): ペイロードデータ（例: `{"sub": "user_id"}`）
- `expires_delta` (Optional[timedelta]): 有効期限（デフォルト: 7日間）

**出力**:
- `str`: JWT文字列

**使用例**:
```python
token = create_access_token(data={"sub": "123"})
# "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### `get_current_user(credentials: HTTPAuthorizationCredentials, db: Session) -> User`
**ファイル**: `auth.py:35-56`

**機能**: JWTトークンからユーザーを取得（認証必須）

**入力**:
- `credentials` (HTTPAuthorizationCredentials): Bearerトークン
- `db` (Session): データベースセッション

**出力**:
- `User`: 認証済みユーザー

**例外**:
- `HTTPException(401)`: トークン無効またはユーザーが存在しない

**使用例**:
```python
@app.get("/api/protected")
async def protected(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username}
```

---

#### `get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials], db: Session) -> Optional[User]`
**ファイル**: `auth.py:58-79`

**機能**: JWTトークンからユーザーを取得（認証オプショナル）

**入力**:
- `credentials` (Optional[HTTPAuthorizationCredentials]): Bearerトークン（なくてもOK）
- `db` (Session): データベースセッション

**出力**:
- `Optional[User]`: 認証済みユーザー（トークンがない場合はNone）

**使用例**:
```python
@app.post("/api/chat")
async def chat(current_user: Optional[User] = Depends(get_current_user_optional)):
    if current_user:
        # ログイン済みユーザー: チャット履歴を保存
        pass
    else:
        # 未ログインユーザー: チャット履歴を保存しない
        pass
```

---

## FastAPIエンドポイント

### 1. HTMLページ

#### `GET /`
**ファイル**: `main.py:70-78`

**機能**: ホームページを表示

**認証**: 不要

**レスポンス**: HTMLResponse

**動作**:
- **ローカル環境** (`ENVIRONMENT=local`): チャット画面（`index.html`）
- **本番環境** (`ENVIRONMENT=production`): ログイン画面（`login.html`）

**使用例**:
```bash
curl http://localhost:8000/
```

---

#### `GET /chat`
**ファイル**: `main.py:80-83`

**機能**: チャットページを表示

**認証**: 不要

**レスポンス**: HTMLResponse（`index.html`）

**使用例**:
```bash
curl http://localhost:8000/chat
```

---

### 2. 設定API

#### `GET /api/config`
**ファイル**: `main.py:85-92`

**機能**: フロントエンド用の設定情報を取得

**認証**: 不要

**入力**: なし

**出力**:
```json
{
  "model": "gpt-4o-mini",
  "environment": "local",
  "skip_auth": true
}
```

**使用例**:
```bash
curl http://localhost:8000/api/config
```

---

### 3. 認証API

#### `POST /api/register`
**ファイル**: `main.py:94-118`

**機能**: 新規ユーザーを登録

**認証**: 不要

**入力**:
```json
{
  "email": "user@example.com",
  "username": "myusername",
  "password": "securepassword123"
}
```

**出力**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**エラー**:
- `400`: Email already registered
- `400`: Username already taken

**使用例**:
```bash
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"test123"}'
```

---

#### `POST /api/login`
**ファイル**: `main.py:120-131`

**機能**: ユーザーログイン

**認証**: 不要

**入力**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**出力**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**エラー**:
- `401`: Incorrect email or password

**使用例**:
```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

---

### 4. チャットAPI

#### `POST /api/chat`
**ファイル**: `main.py:133-310`

**機能**: AIチャット（ストリーミング + Function Calling対応）

**認証**: オプショナル（ログイン済みの場合はチャット履歴を保存）

**入力**:
```json
{
  "messages": [
    {"role": "user", "content": "年間需要15000個、発注コスト500円、保管費率25%、単価12円でEOQを計算してください"}
  ],
  "model": "gpt-4o-mini"
}
```

**出力**: Server-Sent Events (text/event-stream)

```
data: {"function_call": {"name": "calculate_eoq_raw", "result": {...}}}

data: {"content": "計算結果"}

data: {"content": "は以下の通りです..."}

data: [DONE]
```

**処理フロー**:
1. ユーザーメッセージをデータベースに保存（ログイン時のみ）
2. システムプロンプト（ツール使用指示）を追加
3. OpenAI API呼び出し（Function Calling有効）
4. Function callがある場合:
   - MCP関数を実行（`execute_mcp_function`）
   - 結果をストリーミング送信
   - 最終応答を生成（ストリーミング）
5. アシスタントメッセージをデータベースに保存（ログイン時のみ）

**特徴**:
- **ストリーミングレスポンス**: リアルタイムでテキストを表示
- **Function Calling**: LLMが自動的にツールを呼び出し
- **日本語対応**: システムプロンプトで日本語出力を強制
- **可視化対応**: グラフや図を自動生成

**使用例**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"messages":[{"role":"user","content":"EOQを計算してください"}]}'
```

---

### 5. 可視化API

#### `GET /api/visualization/{viz_id}`
**ファイル**: `main.py:312-356`

**機能**: 可視化HTMLを取得

**認証**: 不要（viz_idはUUIDで推測困難）

**入力**:
- パスパラメータ: `viz_id` (str) - 可視化ID（UUID）

**出力**: HTMLResponse（Plotlyインタラクティブグラフ）

**エラー**:
- `404`: Visualization not found

**処理フロー**:
1. ファイルシステム（`/tmp/visualizations/{viz_id}.html`）から検索
2. ファイルが見つからない場合、メモリキャッシュから検索
3. どちらにもない場合は404エラー

**使用例**:
```bash
curl http://localhost:8000/api/visualization/550e8400-e29b-41d4-a716-446655440000
```

---

### 6. ヘルスチェックAPI

#### `GET /health`
**ファイル**: `main.py:358-361`

**機能**: アプリケーションの稼働状態を確認

**認証**: 不要

**入力**: なし

**出力**:
```json
{
  "status": "ok"
}
```

**使用例**:
```bash
curl http://localhost:8000/health
```

---

## MCP Tools（在庫最適化ツール）

MCP Toolsは、OpenAI Function Callingを通じて自動的に呼び出される在庫最適化関数群です。

### ツール一覧（43種類）

#### カテゴリ別分類

##### 1. EOQ（経済発注量）計算
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `calculate_eoq_raw` | 基本EOQ計算 | mcp_tools.py:262 |
| `calculate_eoq_incremental_discount_raw` | 増分数量割引EOQ | mcp_tools.py:216 |
| `calculate_eoq_all_units_discount_raw` | 全単位数量割引EOQ | mcp_tools.py:170 |
| `visualize_eoq` | EOQ可視化 | mcp_tools.py:1153 |

---

##### 2. 安全在庫計算
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `calculate_safety_stock` | 単一品目安全在庫計算 | mcp_tools.py:300 |
| `optimize_safety_stock_allocation` | マルチエシュロン安全在庫最適化（MESSA） | mcp_tools.py:338 |
| `visualize_safety_stock_network` | 安全在庫ネットワーク可視化 | mcp_tools.py:1136 |

---

##### 3. (Q,R)方策（定量発注方式）
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `optimize_qr_policy` | (Q,R)方策の最適化 | mcp_tools.py:463 |
| `simulate_qr_policy` | (Q,R)方策のシミュレーション | mcp_tools.py:410 |

---

##### 4. (s,S)方策
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `optimize_ss_policy` | (s,S)方策の最適化 | mcp_tools.py:561 |
| `simulate_ss_policy` | (s,S)方策のシミュレーション | mcp_tools.py:508 |

---

##### 5. 基在庫方策
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `simulate_base_stock_policy` | 基在庫シミュレーション（需要配列指定） | mcp_tools.py:879 |
| `base_stock_simulation_using_dist` | 基在庫シミュレーション（分布ベース） | mcp_tools.py:1276 |
| `calculate_base_stock_levels` | 基在庫レベル計算 | mcp_tools.py:921 |
| `simulate_network_base_stock` | ネットワーク基在庫シミュレーション | mcp_tools.py:1241 |

---

##### 6. 定期発注方式
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `optimize_periodic_inventory` | 定期発注最適化（Adam/Momentum/SGD） | mcp_tools.py:1031 |
| `optimize_periodic_with_one_cycle` | Fit One Cycle学習率スケジューラ | mcp_tools.py:1196 |
| `find_optimal_learning_rate_periodic` | 最適学習率探索 | mcp_tools.py:1165 |
| `visualize_periodic_optimization` | 定期発注最適化結果可視化 | mcp_tools.py:1124 |

---

##### 7. 需要分析・予測
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `forecast_demand` | 需要予測（Holt-Winters） | mcp_tools.py:957 |
| `visualize_forecast` | 需要予測結果可視化 | mcp_tools.py:1000 |
| `analyze_demand_pattern` | 需要パターン分析 | mcp_tools.py:636 |
| `find_best_distribution` | 最適確率分布フィッティング | mcp_tools.py:794 |
| `visualize_demand_histogram` | 需要ヒストグラム可視化 | mcp_tools.py:812 |

---

##### 8. その他の在庫計算
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `calculate_wagner_whitin` | Wagner-Whitinアルゴリズム | mcp_tools.py:606 |
| `compare_inventory_policies` | 在庫方策比較 | mcp_tools.py:654 |
| `analyze_inventory_network` | 在庫ネットワーク分析 | mcp_tools.py:359 |

---

##### 9. 可視化
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `visualize_last_optimization` | 直前の最適化結果可視化 | mcp_tools.py:380 |
| `visualize_inventory_simulation` | 在庫シミュレーション可視化 | mcp_tools.py:732 |
| `visualize_simulation_trajectories` | シミュレーション軌道可視化 | mcp_tools.py:1337 |
| `visualize_supply_chain_network` | サプライチェーンネットワーク可視化 | mcp_tools.py:1380 |
| `compare_inventory_costs_visual` | 在庫コスト比較可視化 | mcp_tools.py:834 |

---

##### 10. ユーティリティ
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `generate_sample_data` | サンプルデータ生成 | mcp_tools.py:392 |

---

##### 11. ロットサイズ最適化
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `optimize_lotsizing` | 基本ロットサイズ最適化（単一モード） | mcp_tools.py:1730 |
| `optimize_multimode_lotsizing` | マルチモードロットサイズ最適化 | mcp_tools.py:1780 |
| `visualize_lotsizing_result` | 基本ロットサイズ最適化結果の可視化 | mcp_tools.py:2588 |
| `visualize_multimode_lotsizing_result` | マルチモードロットサイズ最適化結果の可視化 | mcp_tools.py:2651 |
| `generate_lotsize_template` | ロットサイズ最適化用Excelテンプレート生成 | mcp_tools.py:1832 |
| `generate_order_template` | 注文データ入力用Excelテンプレート生成 | mcp_tools.py:1852 |
| `add_lotsize_detailed_sheets` | 期別資源容量の詳細シート追加 | mcp_tools.py:1871 |
| `optimize_lotsizing_from_excel` | ExcelからデータRを読み込んで最適化実行 | mcp_tools.py:1911 |
| `export_lotsizing_result` | 最適化結果のExcelエクスポート | mcp_tools.py:1947 |

---

##### 12. ロジスティクス・ネットワーク設計（LND）
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `solve_lnd` | ロジスティクス・ネットワーク設計最適化 | mcp_tools.py:7516 |
| `customer_aggregation_kmeans` | k-means法による顧客集約 | mcp_tools.py:7576 |
| `customer_aggregation_kmedian` | k-median法による顧客集約 | mcp_tools.py:7636 |
| `elbow_method_lnd` | エルボー法で最適集約数を決定 | mcp_tools.py:7712 |
| `make_network_lnd` | 輸送・配送ネットワーク生成 | mcp_tools.py:7769 |
| `generate_melos_template` | MELOSテンプレートExcel生成 | mcp_tools.py:7820 |
| `solve_lnd_from_excel` | ExcelファイルからLND最適化 | mcp_tools.py:7848 |
| `export_lnd_result` | LND最適化結果のExcelエクスポート | mcp_tools.py:7906 |
| `visualize_lnd_result` | LND最適化結果の地図可視化 | mcp_tools.py:7960 |

---

### ツール詳細仕様

以下、主要なツールの詳細仕様を記載します。

---

#### `calculate_eoq_raw`
**機能**: 基本的な経済発注量（EOQ）を計算

**入力パラメータ**:
```json
{
  "annual_demand": 15000,
  "order_cost": 500.0,
  "holding_cost_rate": 0.25,
  "unit_price": 12.0,
  "backorder_cost": 0.0,
  "visualize": false
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| annual_demand | integer | ✓ | 年間需要量（units/年） |
| order_cost | number | ✓ | 発注固定費用（円/回） |
| holding_cost_rate | number | ✓ | 在庫保管費率（0.25 = 25%） |
| unit_price | number | ✓ | 単価（円/unit） |
| backorder_cost | number | - | バックオーダーコスト（円/unit/日） |
| visualize | boolean | - | 可視化するか（デフォルト: false） |

**出力**:
```json
{
  "success": true,
  "eoq_units": 1000,
  "eoq_days": 24.33,
  "total_cost": 3000.0,
  "order_cost_total": 1500.0,
  "holding_cost_total": 1500.0,
  "backorder_cost_total": 0.0,
  "annual_orders": 15,
  "parameters": {
    "d": 41.1,
    "K": 500.0,
    "h": 0.00822,
    "unit_price": 12.0
  },
  "visualization_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**処理フロー**:
1. 生パラメータを計算用パラメータに変換（`convert_eoq_params_from_raw`）
2. EOQ計算（`calc_eoq_basic`）
3. 可視化リクエストがある場合、グラフを生成
4. 結果を返す

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `calculate_eoq_all_units_discount_raw`
**機能**: 全単位数量割引を考慮したEOQ計算

**入力パラメータ**:
```json
{
  "annual_demand": 15000,
  "order_cost": 500.0,
  "holding_cost_rate": 0.25,
  "price_table": [
    {"quantity": 0, "price": 15.0},
    {"quantity": 1000, "price": 12.0},
    {"quantity": 2000, "price": 10.0}
  ],
  "backorder_cost": 0.0,
  "visualize": false
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| annual_demand | integer | ✓ | 年間需要量（units/年） |
| order_cost | number | ✓ | 発注固定費用（円/回） |
| holding_cost_rate | number | ✓ | 在庫保管費率（0.25 = 25%） |
| price_table | array | ✓ | 単価テーブル [{quantity, price}, ...] |
| backorder_cost | number | - | バックオーダーコスト（円/unit/日） |
| visualize | boolean | - | 可視化するか（デフォルト: false） |

**出力**:
```json
{
  "success": true,
  "eoq_units": 2000,
  "selected_price": 10.0,
  "total_cost": 152500.0,
  "procurement_cost": 150000.0,
  "order_cost_total": 1875.0,
  "holding_cost_total": 625.0,
  "discount_info": {
    "breakpoints": [0, 1000, 2000],
    "prices": [15.0, 12.0, 10.0]
  },
  "visualization_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `calculate_safety_stock`
**機能**: 単一品目の安全在庫レベルを計算

**入力パラメータ**:
```json
{
  "mu": 100.0,
  "sigma": 20.0,
  "LT": 7,
  "b": 50.0,
  "h": 0.5,
  "fc": 10000.0
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| mu | number | ✓ | 平均需要量（units/日） |
| sigma | number | ✓ | 需要の標準偏差 |
| LT | integer | ✓ | リードタイム（日） |
| b | number | ✓ | 品切れ費用（円/unit/日） |
| h | number | ✓ | 在庫保管費用（円/unit/日） |
| fc | number | - | 発注固定費用（円/回）デフォルト: 10000 |

**出力**:
```json
{
  "success": true,
  "safety_stock": 52.96,
  "reorder_point": 752.96,
  "service_level": 0.95,
  "expected_demand_during_lt": 700.0,
  "std_demand_during_lt": 52.92,
  "parameters": {
    "mu": 100.0,
    "sigma": 20.0,
    "LT": 7,
    "b": 50.0,
    "h": 0.5
  }
}
```

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `optimize_safety_stock_allocation`
**機能**: マルチエシュロン在庫ネットワーク全体での安全在庫配置を最適化（MESSA: MEta Safety Stock Allocation）

**入力パラメータ**:
```json
{
  "items_data": "[{\"name\":\"製品A\",\"process_time\":1,\"max_service_time\":2,\"avg_demand\":100,\"demand_std\":20,\"holding_cost\":0.5,\"stockout_cost\":50,\"fixed_cost\":1000}]",
  "bom_data": "[{\"child\":\"部品B\",\"parent\":\"製品A\",\"quantity\":2}]"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| items_data | string | ✓ | 品目データのJSON配列文字列 |
| bom_data | string | ✓ | BOM（部品表）データのJSON配列文字列 |

**items_data構造**:
```json
[
  {
    "name": "製品A",
    "process_time": 1,
    "max_service_time": 2,
    "avg_demand": 100,
    "demand_std": 20,
    "holding_cost": 0.5,
    "stockout_cost": 50,
    "fixed_cost": 1000
  }
]
```

**bom_data構造**:
```json
[
  {
    "child": "部品B",
    "parent": "製品A",
    "quantity": 2
  }
]
```

**出力**:
```json
{
  "success": true,
  "optimal_safety_stocks": {
    "製品A": 45.2,
    "部品B": 90.4
  },
  "total_holding_cost": 67.8,
  "service_levels": {
    "製品A": 0.95,
    "部品B": 0.98
  },
  "network_info": {
    "num_nodes": 2,
    "num_edges": 1,
    "total_items": 2
  }
}
```

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `optimize_qr_policy`
**機能**: (Q,R)方策（連続監視型・定量発注方式）の最適パラメータを計算

**入力パラメータ**:
```json
{
  "mu": 100.0,
  "sigma": 20.0,
  "lead_time": 7,
  "holding_cost": 0.5,
  "stockout_cost": 50.0,
  "fixed_cost": 1000.0,
  "n_samples": 10,
  "n_periods": 100
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| mu | number | ✓ | 1日あたりの平均需要量（units/日） |
| sigma | number | ✓ | 需要の標準偏差 |
| lead_time | integer | ✓ | リードタイム（日） |
| holding_cost | number | ✓ | 在庫保管費用（円/unit/日） |
| stockout_cost | number | ✓ | 品切れ費用（円/unit） |
| fixed_cost | number | ✓ | 固定発注費用（円/回） |
| n_samples | integer | - | シミュレーションサンプル数（デフォルト: 10） |
| n_periods | integer | - | シミュレーション期間（日）（デフォルト: 100） |

**出力**:
```json
{
  "success": true,
  "optimal_Q": 1000,
  "optimal_R": 750,
  "expected_cost": 15000,
  "holding_cost": 7500,
  "stockout_cost": 2500,
  "order_cost": 5000,
  "service_level": 0.95,
  "optimization_details": {
    "iterations": 50,
    "convergence": true
  }
}
```

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `optimize_periodic_inventory`
**機能**: 定期発注方式の最適化（Adam/Momentum/SGD）

**入力パラメータ**:
```json
{
  "items_data": "[{\"name\":\"Stage0\",\"demand_mean\":10,\"demand_std\":2,\"net_replenishment_time\":3,\"h\":0.5}]",
  "bom_data": "[]",
  "algorithm": "adam",
  "learning_rate": 0.01,
  "max_iterations": 100,
  "tolerance": 0.001,
  "beta1": 0.9,
  "beta2": 0.999,
  "backorder_cost": 100.0,
  "visualize": false
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| items_data | string | ✓ | 段階データのJSON配列文字列 |
| bom_data | string | ✓ | BOMデータのJSON配列文字列 |
| algorithm | string | ✓ | "adam" / "momentum" / "sgd" |
| learning_rate | number | ✓ | 学習率（例: 0.01） |
| max_iterations | integer | - | 最大反復回数（デフォルト: 100） |
| tolerance | number | - | 収束判定閾値（デフォルト: 0.001） |
| beta1 | number | - | Adam beta1（デフォルト: 0.9） |
| beta2 | number | - | Adam beta2（デフォルト: 0.999） |
| backorder_cost | number | - | バックオーダーコスト（円/unit） |
| visualize | boolean | - | 可視化するか（デフォルト: false） |

**出力**:
```json
{
  "success": true,
  "optimal_base_stock_levels": {
    "Stage0": 45.2,
    "Stage1": 60.8
  },
  "total_cost": 1250.0,
  "holding_cost": 800.0,
  "backorder_cost": 450.0,
  "convergence_info": {
    "iterations": 78,
    "converged": true,
    "final_gradient_norm": 0.0008
  },
  "visualization_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `forecast_demand`
**機能**: Holt-Winters法による需要予測

**入力パラメータ**:
```json
{
  "historical_demand": [100, 105, 110, 108, 112, 115, 120],
  "forecast_periods": 7,
  "trend": "additive",
  "seasonal": "additive",
  "seasonal_periods": 7,
  "visualize": false
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| historical_demand | array | ✓ | 過去需要データ [100, 105, ...] |
| forecast_periods | integer | ✓ | 予測期間数 |
| trend | string | - | "additive" / "multiplicative" / null |
| seasonal | string | - | "additive" / "multiplicative" / null |
| seasonal_periods | integer | - | 季節周期（デフォルト: 7） |
| visualize | boolean | - | 可視化するか（デフォルト: false） |

**出力**:
```json
{
  "success": true,
  "forecast": [122, 125, 128, 130, 133, 135, 138],
  "confidence_intervals": {
    "lower": [115, 117, 119, 121, 123, 125, 127],
    "upper": [129, 133, 137, 139, 143, 145, 149]
  },
  "trend_component": [0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
  "seasonal_component": [1.0, 1.05, 1.1, 1.0, 1.15, 1.2, 1.25],
  "model_params": {
    "alpha": 0.2,
    "beta": 0.1,
    "gamma": 0.05
  },
  "visualization_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `visualize_last_optimization`
**機能**: 直前に実行した安全在庫最適化結果を可視化

**入力パラメータ**: なし

**出力**:
```json
{
  "success": true,
  "visualization_id": "550e8400-e29b-41d4-a716-446655440004",
  "url": "http://localhost:8000/api/visualization/550e8400-e29b-41d4-a716-446655440004"
}
```

**注意**:
- `optimize_safety_stock_allocation`を事前に実行している必要がある
- ユーザーごとにキャッシュが管理される

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `generate_sample_data`
**機能**: サプライチェーンネットワーク最適化用のサンプルデータを生成

**入力パラメータ**:
```json
{
  "complexity": "standard"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| complexity | string | ✓ | "simple" (3品目) / "standard" (5品目) / "complex" (8品目) |

**出力**:
```json
{
  "success": true,
  "items_data": "[{\"name\":\"製品A\",...}]",
  "bom_data": "[{\"child\":\"部品B\",\"parent\":\"製品A\",\"quantity\":2}]",
  "description": "5品目の標準的なサプライチェーンネットワーク",
  "usage_example": "optimize_safety_stock_allocationに渡してください"
}
```

**実装**: `mcp_tools.py:1401` (execute_mcp_function内)

---

#### `optimize_lotsizing`
**機能**: 基本ロットサイズ最適化（単一モード生産）

**入力パラメータ**:
```json
{
  "item_data": [
    {"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100}
  ],
  "production_data": [
    {"name": "Product1", "SetupTime": 30, "SetupCost": 500, "ProdTime": 2, "ProdCost": 10}
  ],
  "demand": [[100, 120, 110, 130, 140, 125, 135, 145, 150, 160]],
  "resource_data": [
    {"name": "Res1", "period": 0, "capacity": 2000},
    {"name": "Res1", "period": 1, "capacity": 2000}
  ],
  "max_cpu": 60,
  "solver": "CBC",
  "visualize": false
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| item_data | array | ✓ | 品目データ配列 |
| production_data | array | ✓ | 生産データ配列 |
| demand | array | ✓ | 需要データ（2次元配列: [品目][期]） |
| resource_data | array | ✓ | 資源データ配列 |
| max_cpu | integer | - | 最大計算時間（秒）（デフォルト: 60） |
| solver | string | - | ソルバー（"CBC" / "GRB"）（デフォルト: "CBC"） |
| visualize | boolean | - | 可視化するか（デフォルト: false） |

**item_data構造**:
- `name`: 品目名
- `inv_cost`: 在庫保管費用（円/期/unit）
- `safety_inventory`: 安全在庫量（下限）
- `target_inventory`: 目標在庫量（上限）
- `initial_inventory`: 初期在庫量

**production_data構造**:
- `name`: 品目名
- `SetupTime`: 段取り時間（分）
- `SetupCost`: 段取り費用（円）
- `ProdTime`: 生産時間（分/unit）
- `ProdCost`: 生産費用（円/unit）

**resource_data構造**:
- `name`: 資源名
- `period`: 期
- `capacity`: 容量（分）

**出力**:
```json
{
  "status": "success",
  "objective_value": 16185.0,
  "message": "最適化が完了しました",
  "solver_status": "Optimal",
  "production_plan": {
    "Product1": [0, 245, 0, 0, 280, 0, 0, 295, 0, 0]
  },
  "inventory_levels": {
    "Product1": [100, 0, 125, 15, 0, 140, 15, 0, 150, 0]
  },
  "violated_constraints": []
}
```

**実装**: `mcp_tools.py:6417-6526`

---

#### `optimize_multimode_lotsizing`
**機能**: マルチモードロットサイズ最適化（複数の生産モードから最適なモードと生産量を選択）

**入力パラメータ**:
```json
{
  "item_data": [
    {"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100, "final_inventory": 50}
  ],
  "resource_data": [
    {"name": "Machine1", "capacity": 8000}
  ],
  "process_data": [
    {"item": "Product1", "mode": "Fast", "setup_cost": 500, "prod_cost": 15, "n_resources": 1},
    {"item": "Product1", "mode": "Slow", "setup_cost": 300, "prod_cost": 12, "n_resources": 1}
  ],
  "bom_data": [],
  "usage_data": [
    {"item": "Product1", "mode": "Fast", "resource": "Machine1", "setup_time": 60, "prod_time": 5},
    {"item": "Product1", "mode": "Slow", "resource": "Machine1", "setup_time": 30, "prod_time": 8}
  ],
  "demand": {"0,Product1": 100, "1,Product1": 120, "2,Product1": 110},
  "capacity": {"0,Machine1": 8000, "1,Machine1": 8000, "2,Machine1": 8000},
  "T": 3,
  "visualize": false
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| item_data | array | ✓ | 品目データ配列 |
| resource_data | array | ✓ | 資源データ配列 |
| process_data | array | ✓ | 工程データ配列（モード別） |
| bom_data | array | ✓ | BOM（部品表）データ配列 |
| usage_data | array | ✓ | 資源使用データ配列 |
| demand | object | ✓ | 需要データ（辞書形式: "期,品目": 需要量） |
| capacity | object | ✓ | 容量データ（辞書形式: "期,資源": 容量） |
| T | integer | ✓ | 計画期間数 |
| visualize | boolean | - | 可視化するか（デフォルト: false） |

**出力**:
```json
{
  "status": "success",
  "objective_value": 7930.0,
  "message": "マルチモードロットサイズ最適化が完了しました",
  "solver_status": "Optimal",
  "production_plan": {
    "Product1,Fast": [100, 0, 110],
    "Product1,Slow": [0, 120, 0]
  },
  "inventory_levels": {
    "Product1": [100, 0, 0]
  }
}
```

**実装**: `mcp_tools.py:6607-6710`

---

#### `visualize_lotsizing_result`
**機能**: 直前に実行した基本ロットサイズ最適化（`optimize_lotsizing`）の結果を可視化

**入力パラメータ**: なし

**出力**:
```json
{
  "status": "success",
  "inventory_visualization_id": "550e8400-e29b-41d4-a716-446655440010",
  "inventory_visualization_url": "/api/visualization/550e8400-e29b-41d4-a716-446655440010",
  "production_visualization_id": "550e8400-e29b-41d4-a716-446655440011",
  "production_visualization_url": "/api/visualization/550e8400-e29b-41d4-a716-446655440011",
  "message": "基本ロットサイズ最適化の可視化が完成しました。",
  "violated_constraints": []
}
```

**可視化内容**:
1. **在庫推移グラフ** (`inventory_visualization_url`):
   - 各品目の在庫量の時系列推移
   - 安全在庫・目標在庫のライン表示

2. **生産量・資源使用グラフ** (`production_visualization_url`):
   - 各品目の期別生産量（棒グラフ）
   - 資源容量制約のライン表示

**注意**:
- `optimize_lotsizing`を事前に実行している必要がある
- ユーザーごとにキャッシュが管理される
- キャッシュは最後の最適化結果のみ保持

**実装**: `mcp_tools.py:2588-2649`

---

#### `visualize_multimode_lotsizing_result`
**機能**: 直前に実行したマルチモードロットサイズ最適化（`optimize_multimode_lotsizing`）の結果を可視化

**入力パラメータ**: なし

**出力**:
```json
{
  "status": "success",
  "inventory_visualization_id": "550e8400-e29b-41d4-a716-446655440012",
  "inventory_visualization_url": "/api/visualization/550e8400-e29b-41d4-a716-446655440012",
  "production_visualization_id": "550e8400-e29b-41d4-a716-446655440013",
  "production_visualization_url": "/api/visualization/550e8400-e29b-41d4-a716-446655440013",
  "message": "マルチモードロットサイズ最適化の可視化が完成しました。",
  "periods": 5
}
```

**可視化内容**:
1. **在庫推移グラフ** (`inventory_visualization_url`):
   - 各品目の在庫量の時系列推移
   - 在庫上下限のライン表示

2. **資源別生産量グラフ** (`production_visualization_url`):
   - 資源ごとのサブプロット
   - モード別生産量（積み上げ棒グラフ）
   - 資源容量制約のライン表示

**注意**:
- `optimize_multimode_lotsizing`を事前に実行している必要がある
- ユーザーごとにキャッシュが管理される

**実装**: `mcp_tools.py:2651-2716`

---

#### `generate_lotsize_template`
**機能**: ロットサイズ最適化用のExcelテンプレートを生成

**入力パラメータ**:
```json
{
  "output_filepath": "lotsize_master.xlsx",
  "include_bom": true
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| output_filepath | string | ✓ | 出力ファイルパス |
| include_bom | boolean | - | BOM関連シートを含めるか（デフォルト: false） |

**出力**:
```json
{
  "status": "success",
  "filepath": "lotsize_master.xlsx",
  "include_bom": true,
  "message": "ロットサイズ最適化用のExcelテンプレートを生成しました",
  "sheets_created": ["品目", "工程", "資源", "部品展開表", "資源必要量"]
}
```

**生成されるシート**:
1. **品目**: 品目マスタ（在庫費用、在庫上下限、初期・最終在庫量）
2. **工程**: 工程マスタ（段取り費用・時間、生産費用・時間）
3. **資源**: 資源マスタ（稼働時間上限）
4. **部品展開表** (include_bom=trueの場合): BOM構造
5. **資源必要量** (include_bom=trueの場合): モード別資源使用量

**実装**: `mcp_tools.py:6786-6830`

---

#### `generate_order_template`
**機能**: 注文データ入力用のExcelテンプレートを生成

**入力パラメータ**:
```json
{
  "output_filepath": "order_data.xlsx"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| output_filepath | string | ✓ | 出力ファイルパス |

**出力**:
```json
{
  "status": "success",
  "filepath": "order_data.xlsx",
  "message": "注文データ入力用のExcelテンプレートを生成しました"
}
```

**生成されるシート**:
- **注文**: 品目ID、納期、数量の入力欄

**実装**: `mcp_tools.py:6832-6850`

---

#### `add_lotsize_detailed_sheets`
**機能**: 既存のロットサイズマスタに期別資源容量の詳細シートを追加

**入力パラメータ**:
```json
{
  "master_filepath": "lotsize_master.xlsx",
  "output_filepath": "lotsize_master_detailed.xlsx",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "period": 1,
  "period_unit": "日"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| master_filepath | string | ✓ | 入力マスタファイルパス |
| output_filepath | string | ✓ | 出力ファイルパス |
| start_date | string | ✓ | 開始日（YYYY-MM-DD） |
| end_date | string | ✓ | 終了日（YYYY-MM-DD） |
| period | integer | - | 期の長さ（デフォルト: 1） |
| period_unit | string | - | 期の単位（"時" / "日" / "週" / "月"）（デフォルト: "日"） |

**出力**:
```json
{
  "status": "success",
  "filepath": "lotsize_master_detailed.xlsx",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "period": 1,
  "period_unit": "日",
  "num_periods": 31,
  "message": "期別資源容量の詳細シートを追加しました"
}
```

**実装**: `mcp_tools.py:6852-6910`

---

#### `optimize_lotsizing_from_excel`
**機能**: ExcelファイルからデータR読み込んでロットサイズ最適化を実行

**入力パラメータ**:
```json
{
  "master_filepath": "lotsize_master_detailed.xlsx",
  "order_filepath": "order_data.xlsx",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "period": 1,
  "period_unit": "日",
  "max_cpu": 60,
  "solver": "CBC",
  "visualize": false
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| master_filepath | string | ✓ | マスタファイルパス |
| order_filepath | string | ✓ | 注文ファイルパス |
| start_date | string | ✓ | 開始日（YYYY-MM-DD） |
| end_date | string | ✓ | 終了日（YYYY-MM-DD） |
| period | integer | - | 期の長さ（デフォルト: 1） |
| period_unit | string | - | 期の単位（デフォルト: "日"） |
| max_cpu | integer | - | 最大計算時間（秒）（デフォルト: 60） |
| solver | string | - | ソルバー（デフォルト: "CBC"） |
| visualize | boolean | - | 可視化するか（デフォルト: false） |

**出力**:
```json
{
  "status": "success",
  "objective_value": 25430.0,
  "message": "Excelファイルからの最適化が完了しました",
  "solver_status": "Optimal",
  "num_items": 5,
  "num_periods": 31,
  "cost_breakdown": {
    "setup_cost": 12000.0,
    "production_cost": 8500.0,
    "inventory_cost": 4930.0
  }
}
```

**実装**: `mcp_tools.py:6912-6998`

---

#### `export_lotsizing_result`
**機能**: 直前に実行したロットサイズ最適化結果をExcelファイルにエクスポート

**入力パラメータ**:
```json
{
  "output_filepath": "optimization_result.xlsx",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "period": 1,
  "period_unit": "日"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| output_filepath | string | ✓ | 出力ファイルパス |
| start_date | string | ✓ | 開始日（YYYY-MM-DD） |
| end_date | string | ✓ | 終了日（YYYY-MM-DD） |
| period | integer | - | 期の長さ（デフォルト: 1） |
| period_unit | string | - | 期の単位（デフォルト: "日"） |

**出力**:
```json
{
  "status": "success",
  "filepath": "optimization_result.xlsx",
  "message": "最適化結果をExcelファイルにエクスポートしました",
  "sheets_created": ["費用内訳", "品目Product1", "品目Product2"]
}
```

**エクスポートされるシート**:
1. **費用内訳**: 各費用項目の合計
2. **品目別シート**: 各品目の在庫量、生産量、需要量、品切れ量、超過量

**注意**:
- `optimize_multimode_lotsizing`を事前に実行している必要がある
- ユーザーごとにキャッシュが管理される

**実装**: `mcp_tools.py:7000-7062`

---

#### `solve_lnd`
**機能**: ロジスティクス・ネットワーク設計（LND）最適化を実行します。MELOS（MEta Logistics Optimization System）を用いて、倉庫配置と物流フローの最適化を行います。

**入力パラメータ**:
```json
{
  "prod_data": [
    {"name": "P1", "weight": 1.0, "volume": 1.0}
  ],
  "cust_data": [
    {"name": "C1", "lat": 35.6762, "lon": 139.6503}
  ],
  "dc_data": [
    {"name": "DC1", "lat": 35.6895, "lon": 139.6917, "fc": 10000, "vc": 0.5, "lb": 0.0, "ub": 5000}
  ],
  "plnt_data": [
    {"name": "Plant1", "lat": 35.4437, "lon": 139.6380}
  ],
  "plnt_prod_data": [
    {"plnt": "Plant1", "prod": "P1", "ub": 10000}
  ],
  "total_demand_data": [
    {"cust": "C1", "prod": "P1", "demand": 100}
  ],
  "trans_data": [
    {"from_node": "Plant1", "to_node": "DC1", "cost": 10.5, "kind": "plnt-dc"},
    {"from_node": "DC1", "to_node": "C1", "cost": 5.0, "kind": "dc-cust"}
  ],
  "dc_num": [1, 3],
  "single_sourcing": true,
  "max_cpu": 60
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| prod_data | array | ✓ | 製品データ配列 |
| cust_data | array | ✓ | 顧客データ配列 |
| dc_data | array | ✓ | 倉庫候補地点データ配列 |
| plnt_data | array | ✓ | 工場データ配列 |
| plnt_prod_data | array | ✓ | 工場-製品データ配列 |
| total_demand_data | array | ✓ | 総需要データ配列 |
| trans_data | array | ✓ | 輸送データ配列 |
| dc_num | array | - | 倉庫数範囲 [min, max]（デフォルト: None） |
| single_sourcing | boolean | - | 単一供給制約（デフォルト: true） |
| max_cpu | integer | - | 最大計算時間（秒）（デフォルト: 60） |

**prod_data構造**:
- `name`: 製品名
- `weight`: 重量
- `volume`: 体積

**cust_data構造**:
- `name`: 顧客名
- `lat`: 緯度
- `lon`: 経度
- `demand`: 需要量（オプション）

**dc_data構造**:
- `name`: 倉庫候補地点名
- `lat`: 緯度
- `lon`: 経度
- `fc`: 固定費用（fixed cost）
- `vc`: 変動費用（variable cost）
- `lb`: 最小容量（lower bound）
- `ub`: 最大容量（upper bound）

**plnt_data構造**:
- `name`: 工場名
- `lat`: 緯度
- `lon`: 経度

**plnt_prod_data構造**:
- `plnt`: 工場名
- `prod`: 製品名
- `ub`: 生産容量（upper bound）

**total_demand_data構造**:
- `cust`: 顧客名
- `prod`: 製品名
- `demand`: 需要量

**trans_data構造**:
- `from_node`: 出発地点名
- `to_node`: 到着地点名
- `kind`: 輸送種別（"plnt-dc" または "dc-cust"）
- `cost`: 輸送費用

**出力**:
```json
{
  "status": "success",
  "solver_status": "Optimal",
  "total_cost": 125430.5,
  "message": "LND最適化が完了しました",
  "flow": [
    {"org": "Plant1", "dst": "DC1", "prod": "P1", "volume": 1500.0}
  ],
  "dc_results": [
    {"name": "DC1", "opened": true, "fixed_cost": 10000, "total_flow": 1500}
  ],
  "num_customers": 10,
  "num_dcs": 3,
  "num_plants": 2,
  "num_products": 2
}
```

**注意**:
- 最適化結果はユーザーごとにキャッシュされ、`visualize_lnd_result`や`export_lnd_result`で利用できます
- `single_sourcing=true`の場合、各顧客は1つの倉庫からのみ供給を受けます

**実装**: `mcp_tools.py:7516-7574`

---

#### `customer_aggregation_kmeans`
**機能**: k-means法を用いて顧客を地理的にクラスタリングし、集約顧客を生成します。大規模問題を解きやすくするための前処理として使用します。

**入力パラメータ**:
```json
{
  "cust_data": [
    {"name": "C1", "lat": 35.6762, "lon": 139.6503},
    {"name": "C2", "lat": 35.6895, "lon": 139.6917}
  ],
  "demand_data": [
    {"cust": "C1", "prod": "P1", "date": "2020-01-01", "demand": 100},
    {"cust": "C2", "prod": "P1", "date": "2020-01-01", "demand": 150}
  ],
  "prod_data": [
    {"name": "P1", "volume": 1.0}
  ],
  "num_of_facilities": 3,
  "start_date": "2020-01-01",
  "end_date": "2020-12-31"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| cust_data | array | ✓ | 顧客データ配列 |
| demand_data | array | ✓ | 需要データ配列（時系列） |
| prod_data | array | ✓ | 製品データ配列 |
| num_of_facilities | integer | ✓ | クラスター数（集約後の顧客数） |
| start_date | string | - | 開始日（YYYY-MM-DD）（デフォルト: None） |
| end_date | string | - | 終了日（YYYY-MM-DD）（デフォルト: None） |

**demand_data構造**:
- `cust`: 顧客名
- `prod`: 製品名
- `date`: 日付（YYYY-MM-DD）
- `demand`: 需要量

**出力**:
```json
{
  "status": "success",
  "num_original_customers": 50,
  "num_clusters": 3,
  "cluster_centers": [
    {"name": "AggCust_0", "lat": 35.6762, "lon": 139.6503}
  ],
  "total_demand": [
    {"cust": "AggCust_0", "prod": "P1", "demand": 5000}
  ],
  "message": "k-means法による顧客集約が完了しました"
}
```

**実装**: `mcp_tools.py:7576-7634`

---

#### `customer_aggregation_kmedian`
**機能**: k-median法を用いて、輸送費用を考慮した顧客集約を行います。Lagrange緩和法により最適なクラスタリングを求めます。

**入力パラメータ**:
```json
{
  "cust_data": [
    {"name": "C1", "lat": 35.6762, "lon": 139.6503}
  ],
  "trans_data": [
    {"org": "C1", "dst": "C2", "cost": 15.5, "distance": 10.2}
  ],
  "demand_data": [
    {"cust": "C1", "prod": "P1", "date": "2020-01-01", "demand": 100}
  ],
  "prod_data": [
    {"name": "P1", "volume": 1.0}
  ],
  "num_of_facilities": 3,
  "start_date": "2020-01-01",
  "end_date": "2020-12-31"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| cust_data | array | ✓ | 顧客データ配列 |
| trans_data | array | ✓ | 輸送費用データ配列（顧客間） |
| demand_data | array | ✓ | 需要データ配列（時系列） |
| prod_data | array | ✓ | 製品データ配列 |
| num_of_facilities | integer | ✓ | クラスター数（集約後の顧客数） |
| start_date | string | - | 開始日（YYYY-MM-DD） |
| end_date | string | - | 終了日（YYYY-MM-DD） |

**出力**:
```json
{
  "status": "success",
  "num_original_customers": 50,
  "num_clusters": 3,
  "cluster_medians": [
    {"name": "AggCust_0", "lat": 35.6762, "lon": 139.6503}
  ],
  "total_demand": [
    {"cust": "AggCust_0", "prod": "P1", "demand": 5000}
  ],
  "total_transport_cost": 12500.5,
  "message": "k-median法による顧客集約が完了しました"
}
```

**実装**: `mcp_tools.py:7636-7710`

---

#### `elbow_method_lnd`
**機能**: エルボー法を用いて、顧客集約における最適なクラスター数を決定します。複数のクラスター数で集約を試行し、目的関数値の変化から推奨値を算出します。

**入力パラメータ**:
```json
{
  "cust_data": [
    {"name": "C1", "lat": 35.6762, "lon": 139.6503}
  ],
  "demand_data": [
    {"cust": "C1", "prod": "P1", "date": "2020-01-01", "demand": 100}
  ],
  "prod_data": [
    {"name": "P1", "volume": 1.0}
  ],
  "n_lb": 2,
  "n_ub": 10,
  "method": "kmeans",
  "repetitions": 5
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| cust_data | array | ✓ | 顧客データ配列 |
| demand_data | array | ✓ | 需要データ配列（時系列） |
| prod_data | array | ✓ | 製品データ配列 |
| n_lb | integer | ✓ | クラスター数下限 |
| n_ub | integer | ✓ | クラスター数上限 |
| method | string | - | 集約手法（"kmeans" / "kmedian"）（デフォルト: "kmeans"） |
| repetitions | integer | - | 試行回数（デフォルト: 10） |

**出力**:
```json
{
  "status": "success",
  "recommended_clusters": 5,
  "n_range": [2, 3, 4, 5, 6, 7, 8, 9, 10],
  "objective_values": [15000.5, 12500.3, 10200.1, 8500.0, 8400.5, 8380.2, 8375.0, 8372.5, 8371.0],
  "message": "エルボー法により推奨クラスター数を決定しました"
}
```

**注意**:
- 目的関数値の減少率が大きく変化するポイント（エルボー）を推奨クラスター数とします
- `method="kmedian"`の場合は輸送費用データも必要です

**実装**: `mcp_tools.py:7712-7767`

---

#### `make_network_lnd`
**機能**: 工場-倉庫-顧客間の輸送ネットワークを生成します。距離閾値に基づいてルートを作成し、輸送費用を計算します。

**入力パラメータ**:
```json
{
  "cust_data": [
    {"name": "C1", "lat": 35.6762, "lon": 139.6503}
  ],
  "dc_data": [
    {"name": "DC1", "lat": 35.6895, "lon": 139.6917}
  ],
  "plnt_data": [
    {"name": "Plant1", "lat": 35.4437, "lon": 139.6380}
  ],
  "plnt_dc_threshold": 1000.0,
  "dc_cust_threshold": 500.0,
  "plnt_dc_cost": 1.0,
  "dc_cust_cost": 1.5
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| cust_data | array | ✓ | 顧客データ配列 |
| dc_data | array | ✓ | 倉庫候補地点データ配列 |
| plnt_data | array | ✓ | 工場データ配列 |
| plnt_dc_threshold | number | ✓ | 工場-倉庫間の最大距離（km） |
| dc_cust_threshold | number | ✓ | 倉庫-顧客間の最大距離（km） |
| plnt_dc_cost | number | ✓ | 工場-倉庫間の輸送費用係数（円/km） |
| dc_cust_cost | number | ✓ | 倉庫-顧客間の輸送費用係数（円/km） |

**出力**:
```json
{
  "status": "success",
  "num_routes": 150,
  "num_plnt_dc_routes": 50,
  "num_dc_cust_routes": 100,
  "routes": [
    {"org": "Plant1", "dst": "DC1", "cost": 30.2, "distance": 30.2}
  ],
  "message": "輸送ネットワークを生成しました"
}
```

**実装**: `mcp_tools.py:7769-7817`

---

#### `generate_melos_template`
**機能**: MELOS用のExcelテンプレートファイルを生成します。顧客、倉庫候補地点、工場、製品の各シートを作成します。

**入力パラメータ**:
```json
{
  "output_filepath": "melos_template.xlsx"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| output_filepath | string | ✓ | 出力ファイルパス |

**出力**:
```json
{
  "status": "success",
  "filepath": "melos_template.xlsx",
  "sheets_created": ["顧客", "倉庫候補地点", "工場", "製品"],
  "message": "MELOSテンプレートを生成しました"
}
```

**生成されるシート**:
1. **顧客**: name, lat, lng, demand列
2. **倉庫候補地点**: name, lat, lng, fixed_cost, capacity列
3. **工場**: name, lat, lng列
4. **製品**: name, volume列

**実装**: `mcp_tools.py:7820-7846`

---

#### `solve_lnd_from_excel`
**機能**: Excelファイルからデータを読み込み、LND最適化を実行します。MELOSテンプレート形式のExcelファイルに対応しています。

**入力パラメータ**:
```json
{
  "filepath": "melos_data.xlsx",
  "dc_num": [1, 3],
  "single_sourcing": true,
  "max_cpu": 60
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filepath | string | ✓ | 入力Excelファイルパス |
| dc_num | array | - | 倉庫数範囲 [min, max]（デフォルト: None） |
| single_sourcing | boolean | - | 単一供給制約（デフォルト: true） |
| max_cpu | integer | - | 最大計算時間（秒）（デフォルト: 60） |

**必要なExcelシート**:
- **顧客**: name, lat, lng列（必須）
- **倉庫候補地点**: name, lat, lng, fixed_cost, capacity列（必須）
- **工場**: name, lat, lng列（必須）
- **製品**: name, volume列（必須）
- **需要**: cust, prod, demand列（必須）
- **工場-製品**: plnt, prod, capacity列（必須）

**出力**:
```json
{
  "status": "success",
  "solver_status": "Optimal",
  "total_cost": 125430.5,
  "message": "ExcelファイルからのLND最適化が完了しました",
  "flow": [...],
  "dc_results": [...],
  "num_customers": 10,
  "num_dcs": 3,
  "num_plants": 2
}
```

**実装**: `mcp_tools.py:7848-7904`

---

#### `export_lnd_result`
**機能**: 直前に実行したLND最適化結果をExcelファイルにエクスポートします。フロー、倉庫開設状況、費用内訳などを出力します。

**入力パラメータ**:
```json
{
  "output_filepath": "lnd_result.xlsx"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| output_filepath | string | ✓ | 出力ファイルパス |

**出力**:
```json
{
  "status": "success",
  "filepath": "lnd_result.xlsx",
  "sheets_created": ["フロー", "倉庫開設状況", "費用内訳"],
  "message": "LND最適化結果をExcelファイルにエクスポートしました"
}
```

**エクスポートされるシート**:
1. **フロー**: org, dst, prod, volume列（物流フロー詳細）
2. **倉庫開設状況**: name, opened, fixed_cost, total_flow列
3. **費用内訳**: 輸送費用、固定費用、総費用

**注意**:
- `solve_lnd`または`solve_lnd_from_excel`を事前に実行している必要があります
- ユーザーごとにキャッシュが管理されます

**実装**: `mcp_tools.py:7906-7957`

---

#### `visualize_lnd_result`
**機能**: LND最適化結果を地図上に可視化します。顧客、倉庫、工場の位置と物流フローをインタラクティブなPlotlyマップで表示します。

**入力パラメータ**:
```json
{}
```

パラメータなし（直前の最適化結果を使用）

**出力**:
```json
{
  "status": "success",
  "visualization_url": "/api/visualization/550e8400-e29b-41d4-a716-446655440000",
  "visualization_id": "550e8400-e29b-41d4-a716-446655440000",
  "num_customers": 10,
  "num_dcs": 3,
  "num_plants": 2,
  "num_flows": 25,
  "message": "LND最適化結果の可視化が完了しました"
}
```

**可視化内容**:
- 顧客位置（青色マーカー）
- 倉庫位置（緑色マーカー、サイズは物流量に比例）
- 工場位置（赤色マーカー）
- 物流フロー（矢印、太さは物流量に比例）

**注意**:
- `solve_lnd`または`solve_lnd_from_excel`を事前に実行している必要があります
- 可視化結果は`/api/visualization/{viz_id}`でアクセス可能

**実装**: `mcp_tools.py:7960-8023`

---

### ロットサイズ最適化ツールの実行例

以下は、Phase 1, 2, 3のロットサイズ最適化ツールをcurlコマンドで実行する例です。

#### 前提条件

JWT認証トークンを取得する必要があります：

```bash
# 1. ログインしてトークンを取得
curl -X POST https://web-production-1ed39.up.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'

# レスポンス例:
# {"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer"}

# 2. トークンを環境変数に設定
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Phase 1: 基本最適化ツールの実行例

##### 例1: 基本ロットサイズ最適化

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/optimize_lotsizing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_data": [
      {"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100}
    ],
    "production_data": [
      {"name": "Product1", "SetupTime": 30, "SetupCost": 500, "ProdTime": 2, "ProdCost": 10}
    ],
    "demand": [[100, 120, 110, 130, 140]],
    "resource_data": [
      {"name": "Res1", "period": 0, "capacity": 2000},
      {"name": "Res1", "period": 1, "capacity": 2000},
      {"name": "Res1", "period": 2, "capacity": 2000},
      {"name": "Res1", "period": 3, "capacity": 2000},
      {"name": "Res1", "period": 4, "capacity": 2000}
    ],
    "max_cpu": 60,
    "solver": "CBC",
    "visualize": false
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "objective_value": 8185.0,
  "message": "最適化が完了しました",
  "solver_status": "Optimal",
  "production_plan": {
    "Product1": [0, 245, 0, 0, 280]
  },
  "inventory_levels": {
    "Product1": [100, 0, 125, 15, 0]
  },
  "violated_constraints": []
}
```

##### 例2: マルチモードロットサイズ最適化

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/optimize_multimode_lotsizing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_data": [
      {"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100, "final_inventory": 50}
    ],
    "resource_data": [
      {"name": "Machine1", "capacity": 8000}
    ],
    "process_data": [
      {"item": "Product1", "mode": "Fast", "setup_cost": 500, "prod_cost": 15, "n_resources": 1},
      {"item": "Product1", "mode": "Slow", "setup_cost": 300, "prod_cost": 12, "n_resources": 1}
    ],
    "bom_data": [],
    "usage_data": [
      {"item": "Product1", "mode": "Fast", "resource": "Machine1", "setup_time": 60, "prod_time": 5},
      {"item": "Product1", "mode": "Slow", "resource": "Machine1", "setup_time": 30, "prod_time": 8}
    ],
    "demand": {"0,Product1": 100, "1,Product1": 120, "2,Product1": 110, "3,Product1": 130, "4,Product1": 140},
    "capacity": {"0,Machine1": 8000, "1,Machine1": 8000, "2,Machine1": 8000, "3,Machine1": 8000, "4,Machine1": 8000},
    "T": 5,
    "visualize": false
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "objective_value": 7930.0,
  "message": "マルチモードロットサイズ最適化が完了しました",
  "solver_status": "Optimal",
  "production_plan": {
    "Product1,Fast": [100, 0, 110, 0, 140],
    "Product1,Slow": [0, 120, 0, 130, 0]
  },
  "inventory_levels": {
    "Product1": [100, 0, 0, 0, 0]
  }
}
```

#### Phase 3: 可視化ツールの実行例

##### 例3: 基本ロットサイズ最適化結果の可視化

```bash
# Step 1: 最適化を実行（上記の例1を実行）

# Step 2: 可視化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_lotsizing_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**レスポンス例**:
```json
{
  "status": "success",
  "inventory_visualization_id": "37c53e34-0cb0-4d23-86c5-ac3bb349b4fc",
  "inventory_visualization_url": "/api/visualization/37c53e34-0cb0-4d23-86c5-ac3bb349b4fc",
  "production_visualization_id": "2828e684-4240-4672-9269-0a61443ff563",
  "production_visualization_url": "/api/visualization/2828e684-4240-4672-9269-0a61443ff563",
  "message": "基本ロットサイズ最適化の可視化が完成しました。",
  "violated_constraints": []
}
```

可視化を表示するには：
```bash
# 在庫推移グラフを表示
open "https://web-production-1ed39.up.railway.app/api/visualization/37c53e34-0cb0-4d23-86c5-ac3bb349b4fc"

# 生産量・資源使用グラフを表示
open "https://web-production-1ed39.up.railway.app/api/visualization/2828e684-4240-4672-9269-0a61443ff563"
```

##### 例4: マルチモードロットサイズ最適化結果の可視化

```bash
# Step 1: マルチモード最適化を実行（上記の例2を実行）

# Step 2: 可視化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_multimode_lotsizing_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**レスポンス例**:
```json
{
  "status": "success",
  "inventory_visualization_id": "68baba1c-7049-458b-a735-fc8689bd91d7",
  "inventory_visualization_url": "/api/visualization/68baba1c-7049-458b-a735-fc8689bd91d7",
  "production_visualization_id": "12c3c40e-9c14-44a7-866a-3bfca710cfd7",
  "production_visualization_url": "/api/visualization/12c3c40e-9c14-44a7-866a-3bfca710cfd7",
  "message": "マルチモードロットサイズ最適化の可視化が完成しました。",
  "periods": 5
}
```

#### Phase 2: Excel関連ツールの実行例

##### 例5: ロットサイズテンプレート生成

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_lotsize_template \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_filepath": "my_lotsize_master.xlsx",
    "include_bom": true
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "filepath": "my_lotsize_master.xlsx",
  "include_bom": true,
  "message": "ロットサイズ最適化用のExcelテンプレートを生成しました",
  "sheets_created": ["品目", "工程", "資源", "部品展開表", "資源必要量"]
}
```

##### 例6: 注文テンプレート生成

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_order_template \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_filepath": "my_order_data.xlsx"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "filepath": "my_order_data.xlsx",
  "message": "注文データ入力用のExcelテンプレートを生成しました"
}
```

##### 例7: 期別詳細シート追加

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/add_lotsize_detailed_sheets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "master_filepath": "my_lotsize_master.xlsx",
    "output_filepath": "my_lotsize_master_detailed.xlsx",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "period": 1,
    "period_unit": "日"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "filepath": "my_lotsize_master_detailed.xlsx",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "period": 1,
  "period_unit": "日",
  "num_periods": 31,
  "message": "期別資源容量の詳細シートを追加しました"
}
```

##### 例8: マルチモードロットサイズ最適化（複数生産モード対応）

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/optimize_multimode_lotsizing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_data": [
      {"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100, "final_inventory": 50}
    ],
    "resource_data": [
      {"name": "Machine1", "capacity": 8000}
    ],
    "process_data": [
      {"item": "Product1", "mode": "Fast", "setup_cost": 500, "prod_cost": 15, "n_resources": 1},
      {"item": "Product1", "mode": "Slow", "setup_cost": 300, "prod_cost": 12, "n_resources": 1}
    ],
    "bom_data": [],
    "usage_data": [
      {"item": "Product1", "mode": "Fast", "resource": "Machine1", "setup_time": 60, "prod_time": 5},
      {"item": "Product1", "mode": "Slow", "resource": "Machine1", "setup_time": 30, "prod_time": 8}
    ],
    "demand": {"0,Product1": 100, "1,Product1": 120, "2,Product1": 110, "3,Product1": 130, "4,Product1": 140},
    "capacity": {"0,Machine1": 8000, "1,Machine1": 8000, "2,Machine1": 8000, "3,Machine1": 8000, "4,Machine1": 8000},
    "T": 5,
    "visualize": true
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "objective_value": 7850.0,
  "message": "マルチモード最適化が完了しました",
  "solver_status": "Optimal",
  "periods": 5,
  "items_count": 1,
  "inventory_visualization_id": "a3b4c5d6-e7f8-9012-3456-789abcdef012",
  "inventory_visualization_url": "/api/visualization/a3b4c5d6-e7f8-9012-3456-789abcdef012",
  "production_visualization_id": "b4c5d6e7-f890-1234-5678-9abcdef01234",
  "production_visualization_url": "/api/visualization/b4c5d6e7-f890-1234-5678-9abcdef01234"
}
```

##### 例9: 最適化結果の可視化

```bash
# Step 1: まず基本ロットサイズ最適化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/optimize_lotsizing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_data": [{"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100}],
    "production_data": [{"name": "Product1", "SetupTime": 30, "SetupCost": 500, "ProdTime": 2, "ProdCost": 10}],
    "demand": [[100, 120, 110, 130, 140]],
    "resource_data": [
      {"name": "Res1", "period": 0, "capacity": 2000},
      {"name": "Res1", "period": 1, "capacity": 2000},
      {"name": "Res1", "period": 2, "capacity": 2000},
      {"name": "Res1", "period": 3, "capacity": 2000},
      {"name": "Res1", "period": 4, "capacity": 2000}
    ],
    "max_cpu": 60,
    "solver": "CBC",
    "visualize": false
  }'

# Step 2: 最適化結果を可視化
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_lotsizing_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**レスポンス例**:
```json
{
  "status": "success",
  "inventory_visualization_id": "abc123-def456",
  "inventory_visualization_url": "/api/visualization/abc123-def456",
  "production_visualization_id": "ghi789-jkl012",
  "production_visualization_url": "/api/visualization/ghi789-jkl012",
  "message": "基本ロットサイズ最適化の可視化が完成しました。",
  "violated_constraints": []
}
```

#### 典型的なワークフロー例

##### ワークフロー1: JSONデータから直接最適化→可視化

```bash
# Step 1: 基本ロットサイズ最適化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/optimize_lotsizing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_data": [{"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100}],
    "production_data": [{"name": "Product1", "SetupTime": 30, "SetupCost": 500, "ProdTime": 2, "ProdCost": 10}],
    "demand": [[100, 120, 110, 130, 140]],
    "resource_data": [
      {"name": "Res1", "period": 0, "capacity": 2000},
      {"name": "Res1", "period": 1, "capacity": 2000},
      {"name": "Res1", "period": 2, "capacity": 2000},
      {"name": "Res1", "period": 3, "capacity": 2000},
      {"name": "Res1", "period": 4, "capacity": 2000}
    ],
    "max_cpu": 60,
    "solver": "CBC",
    "visualize": false
  }'

# Step 2: 可視化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_lotsizing_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

##### ワークフロー2: Excelファイル経由で最適化→エクスポート

```bash
# Step 1: テンプレート生成
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_lotsize_template \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"output_filepath":"master.xlsx","include_bom":true}'

# Step 2: 注文テンプレート生成
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_order_template \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"output_filepath":"order.xlsx"}'

# Step 3: 期別詳細シート追加
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/add_lotsize_detailed_sheets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "master_filepath":"master.xlsx",
    "output_filepath":"master_detailed.xlsx",
    "start_date":"2025-01-01",
    "end_date":"2025-01-31",
    "period":1,
    "period_unit":"日"
  }'

# [手動] Step 4: Excelファイルにデータを入力

# Step 5: Excelから最適化
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/optimize_lotsizing_from_excel \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "master_filepath":"master_detailed.xlsx",
    "order_filepath":"order.xlsx",
    "start_date":"2025-01-01",
    "end_date":"2025-01-31",
    "period":1,
    "period_unit":"日",
    "max_cpu":60,
    "solver":"CBC",
    "visualize":false
  }'

# Step 6: 結果をExcelにエクスポート
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/export_lotsizing_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_filepath":"result.xlsx",
    "start_date":"2025-01-01",
    "end_date":"2025-01-31",
    "period":1,
    "period_unit":"日"
  }'
```

#### ローカル環境での実行例

ローカル開発環境（`ENVIRONMENT=local`）では、認証なしで実行できます：

```bash
# ローカル環境（認証不要）
curl -X POST http://localhost:8000/api/tools/optimize_lotsizing \
  -H "Content-Type: application/json" \
  -d '{
    "item_data": [{"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100}],
    "production_data": [{"name": "Product1", "SetupTime": 30, "SetupCost": 500, "ProdTime": 2, "ProdCost": 10}],
    "demand": [[100, 120, 110]],
    "resource_data": [
      {"name": "Res1", "period": 0, "capacity": 2000},
      {"name": "Res1", "period": 1, "capacity": 2000},
      {"name": "Res1", "period": 2, "capacity": 2000}
    ],
    "max_cpu": 60,
    "solver": "CBC"
  }'
```

---

### LNDツールの実行例

以下は、Phase 1, 2, 3のLND（ロジスティクス・ネットワーク設計）ツールをcurlコマンドで実行する例です。

#### 前提条件

JWT認証トークンを取得する必要があります：

```bash
# 1. ログインしてトークンを取得
curl -X POST https://web-production-1ed39.up.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'

# 2. トークンを環境変数に設定
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Phase 1: 基本最適化ツールの実行例

##### 例1: LND最適化実行

小規模データでLND最適化を実行する例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/solve_lnd \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prod_data": [
      {"name": "A", "weight": 2, "volume": 0},
      {"name": "B", "weight": 5, "volume": 0}
    ],
    "cust_data": [
      {"name": "札幌市", "lat": 43.06417, "lon": 141.34694},
      {"name": "青森市", "lat": 40.82444, "lon": 140.74}
    ],
    "dc_data": [
      {"name": "札幌市", "lat": 43.06417, "lon": 141.34694, "fc": 10037, "vc": 0.4325, "lb": 0.0, "ub": 501136.2},
      {"name": "青森市", "lat": 40.82444, "lon": 140.74, "fc": 10235, "vc": 0.4146, "lb": 0.0, "ub": 501136.2}
    ],
    "plnt_data": [
      {"name": "Odawara", "lat": 35.25642, "lon": 139.15356}
    ],
    "plnt_prod_data": [
      {"plnt": "Odawara", "prod": "A", "ub": 99999999.0},
      {"plnt": "Odawara", "prod": "B", "ub": 99999999.0}
    ],
    "total_demand_data": [
      {"cust": "札幌市", "prod": "A", "demand": 1976},
      {"cust": "札幌市", "prod": "B", "demand": 18554},
      {"cust": "青森市", "prod": "A", "demand": 1428},
      {"cust": "青森市", "prod": "B", "demand": 13403}
    ],
    "trans_data": [
      {"from_node": "Odawara", "to_node": "札幌市", "cost": 885.0, "kind": "plnt-dc"},
      {"from_node": "Odawara", "to_node": "青森市", "cost": 631.0, "kind": "plnt-dc"},
      {"from_node": "札幌市", "to_node": "札幌市", "cost": 0.0, "kind": "dc-cust"},
      {"from_node": "青森市", "to_node": "青森市", "cost": 0.0, "kind": "dc-cust"}
    ],
    "dc_num": [1, 2],
    "single_sourcing": true,
    "max_cpu": 60
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "solver_status": 2,
  "message": "最適化が完了しました",
  "flow": [
    {"org": "Odawara", "dst": "札幌市", "prod": "A", "volume": 1976.0},
    {"org": "Odawara", "dst": "札幌市", "prod": "B", "volume": 18554.0},
    {"org": "Odawara", "dst": "青森市", "prod": "A", "volume": 1428.0},
    {"org": "Odawara", "dst": "青森市", "prod": "B", "volume": 13403.0},
    {"org": "札幌市", "dst": "札幌市", "prod": "A", "volume": 1976.0},
    {"org": "札幌市", "dst": "札幌市", "prod": "B", "volume": 18554.0},
    {"org": "青森市", "dst": "青森市", "prod": "A", "volume": 1428.0},
    {"org": "青森市", "dst": "青森市", "prod": "B", "volume": 13403.0}
  ],
  "dc_results": [
    {"name": "札幌市", "lat": 43.06417, "lon": 141.34694, "fc": 10037, "vc": 0.4325, "lb": 0.0, "ub": 501136.2, "lower_bound_violation": 0.0, "open_close": 1},
    {"name": "青森市", "lat": 40.82444, "lon": 140.74, "fc": 10235, "vc": 0.4146, "lb": 0.0, "ub": 501136.2, "lower_bound_violation": 0.0, "open_close": 1}
  ],
  "costs": [
    {"cost": "total cost", "value": 51500.0},
    {"cost": "transportation (plant to dc)", "value": 20400.0},
    {"cost": "delivery (dc to customer)", "value": 0.0},
    {"cost": "dc fixed", "value": 20272.0},
    {"cost": "dc variable", "value": 10828.0},
    {"cost": "infeasible penalty", "value": 0.0}
  ],
  "violations": [],
  "total_cost": 51500.0,
  "num_customers": 2,
  "num_dcs": 2,
  "num_plants": 1,
  "num_products": 2
}
```

##### 例2: k-means顧客集約

k-means法で顧客を集約する例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/customer_aggregation_kmeans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cust_data": [
      {"name": "C1", "lat": 35.6762, "lon": 139.6503},
      {"name": "C2", "lat": 35.6895, "lon": 139.6917},
      {"name": "C3", "lat": 35.4437, "lon": 139.6380},
      {"name": "C4", "lat": 35.7090, "lon": 139.7320},
      {"name": "C5", "lat": 35.6580, "lon": 139.7454}
    ],
    "demand_data": [
      {"cust": "C1", "prod": "P1", "date": "2020-01-01", "demand": 100},
      {"cust": "C2", "prod": "P1", "date": "2020-01-01", "demand": 150},
      {"cust": "C3", "prod": "P1", "date": "2020-01-01", "demand": 120},
      {"cust": "C4", "prod": "P1", "date": "2020-01-01", "demand": 80},
      {"cust": "C5", "prod": "P1", "date": "2020-01-01", "demand": 90}
    ],
    "prod_data": [
      {"name": "P1", "volume": 1.0}
    ],
    "num_of_facilities": 2,
    "start_date": "2020-01-01",
    "end_date": "2020-12-31"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "num_original_customers": 5,
  "num_clusters": 2,
  "cluster_centers": [
    {"name": "AggCust_0", "lat": 35.6812, "lon": 139.6873},
    {"name": "AggCust_1", "lat": 35.6835, "lon": 139.7387}
  ],
  "total_demand": [
    {"cust": "AggCust_0", "prod": "P1", "demand": 370},
    {"cust": "AggCust_1", "prod": "P1", "demand": 170}
  ],
  "message": "k-means法による顧客集約が完了しました"
}
```

##### 例3: エルボー法で最適クラスター数決定

エルボー法で推奨クラスター数を求める例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/elbow_method_lnd \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cust_data": [
      {"name": "C1", "lat": 35.6762, "lon": 139.6503},
      {"name": "C2", "lat": 35.6895, "lon": 139.6917},
      {"name": "C3", "lat": 35.4437, "lon": 139.6380},
      {"name": "C4", "lat": 35.7090, "lon": 139.7320},
      {"name": "C5", "lat": 35.6580, "lon": 139.7454}
    ],
    "demand_data": [
      {"cust": "C1", "prod": "P1", "date": "2020-01-01", "demand": 100},
      {"cust": "C2", "prod": "P1", "date": "2020-01-01", "demand": 150}
    ],
    "prod_data": [
      {"name": "P1", "volume": 1.0}
    ],
    "n_lb": 2,
    "n_ub": 5,
    "method": "kmeans",
    "repetitions": 3
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "recommended_clusters": 3,
  "n_range": [2, 3, 4, 5],
  "objective_values": [15000.5, 10200.1, 10150.0, 10140.5],
  "message": "エルボー法により推奨クラスター数を決定しました"
}
```

##### 例4: 輸送ネットワーク生成

距離閾値に基づいて輸送ネットワークを生成する例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/make_network_lnd \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cust_data": [
      {"name": "C1", "lat": 35.6762, "lon": 139.6503},
      {"name": "C2", "lat": 35.6895, "lon": 139.6917}
    ],
    "dc_data": [
      {"name": "DC1", "lat": 35.6895, "lon": 139.6917},
      {"name": "DC2", "lat": 35.4437, "lon": 139.6380}
    ],
    "plnt_data": [
      {"name": "Plant1", "lat": 35.4437, "lon": 139.6380}
    ],
    "plnt_dc_threshold": 1000.0,
    "dc_cust_threshold": 500.0,
    "plnt_dc_cost": 1.0,
    "dc_cust_cost": 1.5
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "num_routes": 6,
  "num_plnt_dc_routes": 2,
  "num_dc_cust_routes": 4,
  "routes": [
    {"org": "Plant1", "dst": "DC1", "cost": 30.2, "distance": 30.2},
    {"org": "Plant1", "dst": "DC2", "cost": 0.0, "distance": 0.0},
    {"org": "DC1", "dst": "C1", "cost": 2.2, "distance": 1.5},
    {"org": "DC1", "dst": "C2", "cost": 0.5, "distance": 0.3}
  ],
  "message": "輸送ネットワークを生成しました"
}
```

#### Phase 2: Excelツールの実行例

##### 例5: MELOSテンプレート生成

空のMELOSテンプレートExcelファイルを生成する例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_melos_template \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_filepath": "melos_template.xlsx"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "filepath": "melos_template.xlsx",
  "sheets_created": ["顧客", "倉庫候補地点", "工場", "製品"],
  "message": "MELOSテンプレートを生成しました"
}
```

##### 例6: ExcelからLND最適化

MELOSテンプレートに入力したデータからLND最適化を実行する例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/solve_lnd_from_excel \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filepath": "filled_melos_data.xlsx",
    "dc_num": [1, 3],
    "single_sourcing": true,
    "max_cpu": 60
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "solver_status": "Optimal",
  "total_cost": 225430.5,
  "message": "ExcelファイルからのLND最適化が完了しました",
  "flow": [...],
  "dc_results": [...],
  "num_customers": 15,
  "num_dcs": 5,
  "num_plants": 3
}
```

##### 例7: LND結果のExcelエクスポート

最適化結果をExcelファイルにエクスポートする例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/export_lnd_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "output_filepath": "lnd_optimization_result.xlsx"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "filepath": "lnd_optimization_result.xlsx",
  "sheets_created": ["フロー", "倉庫開設状況", "費用内訳"],
  "message": "LND最適化結果をExcelファイルにエクスポートしました"
}
```

#### Phase 3: 可視化ツールの実行例

##### 例8: LND最適化結果の地図可視化

最適化結果を地図上に可視化する例：

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_lnd_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**レスポンス例**:
```json
{
  "status": "success",
  "visualization_url": "/api/visualization/550e8400-e29b-41d4-a716-446655440000",
  "visualization_id": "550e8400-e29b-41d4-a716-446655440000",
  "num_customers": 15,
  "num_dcs": 3,
  "num_plants": 2,
  "num_flows": 45,
  "message": "LND最適化結果の可視化が完了しました"
}
```

可視化結果はブラウザで表示できます：

```bash
# 可視化結果にアクセス
open https://web-production-1ed39.up.railway.app/api/visualization/550e8400-e29b-41d4-a716-446655440000
```

#### LNDワークフロー例

以下は、典型的なLND分析ワークフローの例です：

**ワークフロー1: 小規模問題の直接最適化**

```bash
# 1. LND最適化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/solve_lnd \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @small_lnd_data.json

# 2. 結果を可視化
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_lnd_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# 3. 結果をExcelにエクスポート
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/export_lnd_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"output_filepath": "lnd_result.xlsx"}'
```

**ワークフロー2: 大規模問題の顧客集約後最適化**

```bash
# 1. エルボー法で最適クラスター数を決定
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/elbow_method_lnd \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @elbow_data.json
# 推奨クラスター数: 5

# 2. k-means法で顧客を集約
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/customer_aggregation_kmeans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cust_data": [...],
    "demand_data": [...],
    "prod_data": [...],
    "num_of_facilities": 5
  }'

# 3. 集約後のデータでLND最適化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/solve_lnd \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @aggregated_lnd_data.json

# 4. 結果を可視化
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_lnd_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**ワークフロー3: Excel経由での最適化**

```bash
# 1. MELOSテンプレートを生成
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_melos_template \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"output_filepath": "melos_template.xlsx"}'

# 2. テンプレートに手動でデータを入力（Excel上で編集）
# ダウンロード → 編集 → アップロード

# 3. ExcelファイルからLND最適化を実行
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/solve_lnd_from_excel \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filepath": "filled_melos_data.xlsx",
    "dc_num": [2, 5],
    "single_sourcing": true,
    "max_cpu": 120
  }'

# 4. 結果をExcelにエクスポート
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/export_lnd_result \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"output_filepath": "lnd_result.xlsx"}'
```

#### ローカル環境での実行例

ローカル開発環境（`ENVIRONMENT=local`）では、認証なしで実行できます：

```bash
# ローカル環境（認証不要）
curl -X POST http://localhost:8000/api/tools/solve_lnd \
  -H "Content-Type: application/json" \
  -d '{
    "prod_data": [{"name": "P1", "weight": 1.0, "volume": 1.0}],
    "cust_data": [{"name": "C1", "lat": 35.6762, "lon": 139.6503}],
    "dc_data": [{"name": "DC1", "lat": 35.6895, "lon": 139.6917, "fc": 10000, "vc": 0.5, "lb": 0.0, "ub": 5000}],
    "plnt_data": [{"name": "Plant1", "lat": 35.4437, "lon": 139.6380}],
    "plnt_prod_data": [{"plnt": "Plant1", "prod": "P1", "ub": 10000}],
    "total_demand_data": [{"cust": "C1", "prod": "P1", "demand": 100}],
    "trans_data": [
      {"from_node": "Plant1", "to_node": "DC1", "cost": 10.5, "kind": "plnt-dc"},
      {"from_node": "DC1", "to_node": "C1", "cost": 5.0, "kind": "dc-cust"}
    ],
    "dc_num": [1, 2],
    "single_sourcing": true,
    "max_cpu": 60
  }'
```

---

### MCP Tools実装関数

#### `execute_mcp_function(function_name: str, arguments: dict, user_id: int = None) -> dict`
**ファイル**: `mcp_tools.py:1401`

**機能**: MCPツール関数を実行するディスパッチャー

**入力**:
- `function_name` (str): 関数名（例: "calculate_eoq_raw"）
- `arguments` (dict): 関数の引数
- `user_id` (int, optional): ユーザーID（キャッシュ管理用）

**出力**:
- `dict`: 実行結果

**処理フロー**:
1. function_nameに応じて対応する実装関数を呼び出し
2. エラーハンドリング
3. 結果をdict形式で返す
4. 可視化結果はキャッシュに保存

**使用例**:
```python
result = execute_mcp_function(
    "calculate_eoq_raw",
    {
        "annual_demand": 15000,
        "order_cost": 500.0,
        "holding_cost_rate": 0.25,
        "unit_price": 12.0
    },
    user_id=123
)
```

---

#### `get_visualization_html(user_id: int, viz_id: str = None) -> str`
**ファイル**: `mcp_tools.py:144-161`

**機能**: ユーザーの可視化HTMLを取得

**入力**:
- `user_id` (int): ユーザーID
- `viz_id` (str, optional): 可視化ID（UUID）

**出力**:
- `str`: HTML文字列（Plotlyグラフ）

**例外**:
- `KeyError`: キャッシュが見つからない

**使用例**:
```python
html = get_visualization_html(user_id=123, viz_id="550e8400-...")
```

---

## SCRM Tools（サプライチェーンリスク管理ツール）

SCRM Toolsは、MERIODAS（MEta RIsk Oriented Disruption Analysis System）フレームワークを用いて、サプライチェーンネットワークにおける供給混乱リスクを分析するためのツール群です。

### ツール一覧（9種類）

#### カテゴリ別分類

##### 1. データ生成・保存
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `generate_scrm_data` | ベンチマーク問題からSCRMデータ生成 | mcp_tools.py:5004 |
| `save_scrm_data_to_csv` | SCRMデータをCSVファイルに保存 | mcp_tools.py:5102 |

##### 2. データ読み込み
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `load_scrm_data_from_csv` | CSVファイルからSCRMデータを読み込み | mcp_tools.py:5208 |

##### 3. グラフ可視化
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `visualize_scrm_graph` | BOM/工場/生産グラフの可視化 | mcp_tools.py:5271 |

##### 4. リスク分析
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `analyze_supply_chain_risk` | サプライチェーンリスク分析（TTS計算） | mcp_tools.py:5354 |
| `visualize_scrm_network` | リスク分析結果のネットワーク可視化 | mcp_tools.py:5729 |

##### 5. 在庫最適化（途絶リスク対応）
| ツール名 | 機能 | ファイル参照 |
|---------|------|-------------|
| `optimize_scrm_inventory_expected` | 期待値最小化による在庫最適化 | mcp_tools.py:5805 |
| `optimize_scrm_inventory_cvar` | CVaR最小化による在庫最適化（リスク回避型） | mcp_tools.py:5899 |
| `compare_scrm_policies` | 在庫方針比較（期待値 vs CVaR） | mcp_tools.py:5999 |

---

### ツール詳細仕様

#### `generate_scrm_data`
**機能**: ベンチマーク問題例からSCRM（サプライチェーンリスク管理）用のネットワークデータを生成します。BOMグラフ、工場ネットワーク、生産グラフを生成し、需要、容量、パイプライン在庫などのパラメータを設定します。

**入力パラメータ**:
```json
{
  "benchmark_id": "01",
  "n_plants": 3,
  "n_flex": 2,
  "prob": 0.5,
  "capacity_factor": 1.0,
  "production_factor": 1.0,
  "pipeline_factor": 1.0,
  "seed": 1
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| benchmark_id | string | ✓ | ベンチマーク問題のID（"01"〜"38"） |
| n_plants | integer | - | 各階層の工場数（デフォルト: 3） |
| n_flex | integer | - | 各工場で生産可能な製品数（デフォルト: 2） |
| prob | number | - | 工場間の輸送リンク生成確率（0.0〜1.0、デフォルト: 0.5） |
| capacity_factor | number | - | 生産容量の倍率（デフォルト: 1.0） |
| production_factor | number | - | 生産量の倍率（デフォルト: 1.0） |
| pipeline_factor | number | - | パイプライン在庫の倍率（デフォルト: 1.0） |
| seed | integer | - | 乱数シード（デフォルト: 1） |

**出力**:
```json
{
  "status": "success",
  "benchmark_id": "01",
  "total_demand": 1000.0,
  "demand": {
    "('Plant_0', 'Product_A')": 100.0,
    "('Plant_1', 'Product_B')": 150.0
  },
  "upper_bound": {
    "('Plant_0', 'Product_A')": 200.0
  },
  "capacity": {
    "('Plant_0', 'Product_A')": 150.0
  },
  "pipeline": {
    "('Plant_0', 'Product_A')": 50.0
  },
  "network_info": {
    "num_plants": 3,
    "num_products": 5,
    "num_production_nodes": 15,
    "num_edges": 42,
    "n_flex": 2
  },
  "parameters": {
    "n_plants": 3,
    "n_flex": 2,
    "prob": 0.5,
    "capacity_factor": 1.0,
    "production_factor": 1.0,
    "pipeline_factor": 1.0,
    "seed": 1
  }
}
```

**実装**: `mcp_tools.py:5004` (execute_mcp_function内)

---

#### `save_scrm_data_to_csv`
**機能**: 生成したSCRMデータをCSVファイルに保存します。BOM構造、工場間輸送、工場-製品マトリックス、工場データの4つのCSVファイルを生成します。

**入力パラメータ**:
```json
{
  "benchmark_id": "01",
  "filename_suffix": "test_01",
  "n_plants": 3,
  "n_flex": 2,
  "prob": 0.5,
  "capacity_factor": 1.0,
  "production_factor": 1.0,
  "pipeline_factor": 1.0,
  "seed": 1
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| benchmark_id | string | ✓ | ベンチマーク問題のID（"01"〜"38"） |
| filename_suffix | string | ✓ | CSVファイル名のサフィックス |
| n_plants | integer | - | 各階層の工場数（デフォルト: 3） |
| n_flex | integer | - | 各工場で生産可能な製品数（デフォルト: 2） |
| prob | number | - | 工場間の輸送リンク生成確率（デフォルト: 0.5） |
| capacity_factor | number | - | 生産容量の倍率（デフォルト: 1.0） |
| production_factor | number | - | 生産量の倍率（デフォルト: 1.0） |
| pipeline_factor | number | - | パイプライン在庫の倍率（デフォルト: 1.0） |
| seed | integer | - | 乱数シード（デフォルト: 1） |

**出力**:
```json
{
  "status": "success",
  "message": "SCRMデータをCSVファイルに保存しました",
  "files_created": [
    "./data/scrm/bom_test_01.csv",
    "./data/scrm/trans_test_01.csv",
    "./data/scrm/plnt_prod_test_01.csv",
    "./data/scrm/plnt_test_01.csv"
  ],
  "benchmark_id": "01",
  "filename_suffix": "test_01",
  "network_info": {
    "num_plants": 3,
    "num_products": 5,
    "num_production_nodes": 15
  }
}
```

**CSVファイル構造**:
- `bom_{suffix}.csv`: BOM構造（子製品、親製品、使用量）
- `trans_{suffix}.csv`: 工場間輸送リンク（出発工場、到着工場、輸送時間）
- `plnt_prod_{suffix}.csv`: 工場-製品マトリックス（工場、製品、生産可否）
- `plnt_{suffix}.csv`: 工場データ（工場名、需要、在庫上限、生産容量、パイプライン在庫）

**実装**: `mcp_tools.py:5102` (execute_mcp_function内)

---

#### `load_scrm_data_from_csv`
**機能**: 保存されたCSVファイルからSCRMデータを読み込み、ネットワーク構造を復元します。

**入力パラメータ**:
```json
{
  "filename_suffix": "test_01"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filename_suffix | string | ✓ | 読み込むCSVファイル名のサフィックス |

**出力**:
```json
{
  "status": "success",
  "message": "SCRMデータをCSVファイルから読み込みました",
  "files_loaded": [
    "./data/scrm/bom_test_01.csv",
    "./data/scrm/trans_test_01.csv",
    "./data/scrm/plnt_prod_test_01.csv",
    "./data/scrm/plnt_test_01.csv"
  ],
  "demand": {
    "('Plant_0', 'Product_A')": 100.0
  },
  "upper_bound": {
    "('Plant_0', 'Product_A')": 200.0
  },
  "capacity": {
    "('Plant_0', 'Product_A')": 150.0
  },
  "pipeline": {
    "('Plant_0', 'Product_A')": 50.0
  },
  "network_info": {
    "num_bom_nodes": 5,
    "num_bom_edges": 8,
    "num_plants": 3,
    "num_plant_edges": 6,
    "num_production_nodes": 15,
    "num_production_edges": 42,
    "num_products": 5
  }
}
```

**実装**: `mcp_tools.py:5208` (execute_mcp_function内)

---

#### `visualize_scrm_graph`
**機能**: BOMグラフ、工場ネットワークグラフ、または生産グラフを可視化します。NetworkXとPlotlyを使用してインタラクティブなネットワーク図を生成します。

**入力パラメータ**:
```json
{
  "filename_suffix": "test_01",
  "graph_type": "production",
  "title": "生産グラフ",
  "node_size": 30,
  "node_color": "lightblue"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filename_suffix | string | ✓ | 読み込むCSVファイル名のサフィックス |
| graph_type | string | ✓ | グラフの種類（"bom", "plant", "production"） |
| title | string | - | グラフのタイトル（デフォルト: グラフ種類に応じた自動タイトル） |
| node_size | integer | - | ノードのサイズ（デフォルト: 30） |
| node_color | string | - | ノードの色（デフォルト: "lightblue"） |

**出力**:
```json
{
  "status": "success",
  "visualization_id": "550e8400-e29b-41d4-a716-446655440005",
  "url": "http://localhost:8000/api/visualization/550e8400-e29b-41d4-a716-446655440005",
  "graph_type": "production",
  "network_info": {
    "num_nodes": 15,
    "num_edges": 42
  }
}
```

**グラフ種類**:
- `"bom"`: BOMグラフ（部品表の階層構造）
- `"plant"`: 工場ネットワークグラフ（工場間の輸送リンク）
- `"production"`: 生産グラフ（工場グラフとBOMグラフのテンソル積）

**実装**: `mcp_tools.py:5271` (execute_mcp_function内)

---

#### `analyze_supply_chain_risk`
**機能**: MERIODAS（MEta RIsk Oriented Disruption Analysis System）を使用してサプライチェーンリスクを分析します。各ノード（工場-製品の組み合わせ）のTTS（Time-to-Survival: 生存期間）を計算し、供給混乱に対する脆弱性を評価します。

**入力パラメータ**:
```json
{
  "filename_suffix": "test_01"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filename_suffix | string | ✓ | 読み込むCSVファイル名のサフィックス |

**出力**:
```json
{
  "status": "success",
  "survival_times": {
    "('Plant_0', 'Product_A')": 5.0,
    "('Plant_1', 'Product_B')": 3.5,
    "('Plant_2', 'Product_C')": 7.2
  },
  "statistics": {
    "mean_tts": 5.23,
    "min_tts": 2.0,
    "max_tts": 10.5,
    "std_tts": 2.15
  },
  "critical_nodes_top10": [
    {
      "node": "('Plant_1', 'Product_B')",
      "tts": 2.0,
      "risk_level": "critical"
    },
    {
      "node": "('Plant_3', 'Product_D')",
      "tts": 2.5,
      "risk_level": "high"
    }
  ],
  "network_info": {
    "num_nodes_analyzed": 15,
    "num_critical_nodes": 2,
    "num_high_risk_nodes": 3,
    "num_medium_risk_nodes": 5,
    "num_low_risk_nodes": 5
  },
  "filename_suffix": "test_01"
}
```

**TTS（Time-to-Survival）の解釈**:
- **低いTTS（0〜3）**: 非常に脆弱。短期間で在庫切れになる
- **中程度のTTS（3〜7）**: 中程度のリスク。一定期間は対応可能
- **高いTTS（7以上）**: 低リスク。長期間の供給混乱にも耐えられる

**実装**: `mcp_tools.py:5354` (execute_mcp_function内)

---

#### `visualize_scrm_network`
**機能**: サプライチェーンリスク分析結果をネットワーク図として可視化します。各ノードのTTS値に応じて色分けし、リスクの高いノードを視覚的に識別できます。

**入力パラメータ**:
```json
{
  "filename_suffix": "test_01"
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filename_suffix | string | ✓ | 読み込むCSVファイル名のサフィックス |

**出力**:
```json
{
  "status": "success",
  "visualization_id": "550e8400-e29b-41d4-a716-446655440006",
  "url": "http://localhost:8000/api/visualization/550e8400-e29b-41d4-a716-446655440006",
  "network_info": {
    "num_nodes": 15,
    "num_edges": 42
  },
  "statistics": {
    "mean_tts": 5.23,
    "min_tts": 2.0,
    "max_tts": 10.5
  },
  "color_scheme": {
    "critical": "red (TTS < 3)",
    "high_risk": "orange (3 <= TTS < 5)",
    "medium_risk": "yellow (5 <= TTS < 7)",
    "low_risk": "green (TTS >= 7)"
  }
}
```

**可視化の特徴**:
- ノードの色: TTS値に応じて色分け（赤=危険、緑=安全）
- ノードのサイズ: 需要量に比例
- エッジ: サプライチェーンのリンクを表示
- インタラクティブ: ノードをホバーするとTTS値と詳細情報を表示

**実装**: `mcp_tools.py:5729` (execute_mcp_function内)

---

#### `optimize_scrm_inventory_expected`
**機能**: 期待値最小化による在庫最適化を実行します。サプライチェーンの途絶シナリオを考慮し、在庫保管費用と品切れ費用の期待値を最小化する最適在庫量を計算します。

**入力パラメータ**:
```json
{
  "filename_suffix": "test_01",
  "h_cost": {
    "0,Retail_0001": 1.0,
    "1,Retail_0001": 1.0,
    "0,Retail_0003": 1.0
  },
  "b_cost": {
    "0,Retail_0001": 10.0,
    "1,Retail_0001": 10.0,
    "0,Retail_0003": 10.0
  },
  "disruption_prob": {
    "0": 0.1,
    "1": 0.1,
    "2": 0.05
  },
  "TTR": {
    "0": 2,
    "1": 3,
    "2": 2
  },
  "K_max": 2
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filename_suffix | string | ✓ | 読み込むCSVファイル名のサフィックス |
| h_cost | object | ✓ | 在庫保管費用の辞書。キー: '工場番号,製品名'、値: 費用 |
| b_cost | object | ✓ | 品切れ費用の辞書。キー: '工場番号,製品名'、値: 費用 |
| disruption_prob | object | ✓ | 工場の途絶確率の辞書。キー: 工場番号(文字列)、値: 確率(0-1) |
| TTR | object | ✓ | 工場の回復時間(Time To Recover)の辞書。キー: 工場番号(文字列)、値: 期間数 |
| K_max | integer | - | 同時途絶する工場数の上限（デフォルト: 2） |

**出力**:
```json
{
  "status": "success",
  "optimal_inventory": {
    "0,Retail_0001": 150.5,
    "1,Retail_0001": 200.3,
    "0,Retail_0003": 100.0
  },
  "total_cost": 1492.0,
  "expected_inventory_cost": 1492.0,
  "expected_backorder_cost": 0.0,
  "n_scenarios": 45,
  "message": "期待値最小化による在庫最適化が完了しました（シナリオ数: 45）"
}
```

**最適化アルゴリズム**:
- **目的関数**: 期待総費用最小化 = 在庫保管費用 + 期待品切れ費用
- **モデル**: 2段階確率最適化（即時決定変数: 在庫量、リカース変数: バックオーダー量）
- **シナリオ生成**: 工場途絶の組み合わせからシナリオを生成（単一途絶、同時途絶）
- **制約**: BOM制約、生産容量制約、需要満足制約

**適用例**:
- 標準的なリスク対応在庫計画
- コスト効率重視の在庫配置
- 期待値ベースの意思決定

**実装**: `mcp_tools.py:5805` (execute_mcp_function内)

---

#### `optimize_scrm_inventory_cvar`
**機能**: CVaR（Conditional Value at Risk）最小化による在庫最適化を実行します。期待値最小化よりもリスク回避的な最適化で、最悪シナリオに対して頑健な在庫量を計算します。

**入力パラメータ**:
```json
{
  "filename_suffix": "test_01",
  "h_cost": {
    "0,Retail_0001": 1.0,
    "1,Retail_0001": 1.0,
    "0,Retail_0003": 1.0
  },
  "b_cost": {
    "0,Retail_0001": 10.0,
    "1,Retail_0001": 10.0,
    "0,Retail_0003": 10.0
  },
  "disruption_prob": {
    "0": 0.1,
    "1": 0.1,
    "2": 0.05
  },
  "TTR": {
    "0": 2,
    "1": 3,
    "2": 2
  },
  "beta": 0.95,
  "K_max": 2
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filename_suffix | string | ✓ | 読み込むCSVファイル名のサフィックス |
| h_cost | object | ✓ | 在庫保管費用の辞書。キー: '工場番号,製品名'、値: 費用 |
| b_cost | object | ✓ | 品切れ費用の辞書。キー: '工場番号,製品名'、値: 費用 |
| disruption_prob | object | ✓ | 工場の途絶確率の辞書 |
| TTR | object | ✓ | 工場の回復時間の辞書 |
| beta | number | - | 信頼水準（デフォルト: 0.95）。0.95は95%信頼水準を意味 |
| K_max | integer | - | 同時途絶する工場数の上限（デフォルト: 2） |

**出力**:
```json
{
  "status": "success",
  "optimal_inventory": {
    "0,Retail_0001": 180.2,
    "1,Retail_0001": 230.5,
    "0,Retail_0003": 120.0
  },
  "cvar": 1650.5,
  "var": 1580.0,
  "expected_cost": 1520.0,
  "expected_inventory_cost": 1520.0,
  "expected_backorder_cost": 0.0,
  "beta": 0.95,
  "n_scenarios": 45,
  "message": "CVaR最小化による在庫最適化が完了しました（β=0.95, シナリオ数: 45）"
}
```

**最適化アルゴリズム**:
- **目的関数**: CVaR最小化 = θ + (1/(1-β)) * Σ(確率 × 超過費用)
- **VaR (Value at Risk)**: θ = β分位点の費用
- **CVaR**: VaRを超える費用の期待値
- **リスク回避度**: betaが高いほど保守的（0.95 > 0.90）

**適用例**:
- リスク回避的な在庫計画
- 最悪ケースへの備えが重要な場合
- 規制要件で高い信頼性が求められる場合

**実装**: `mcp_tools.py:5899` (execute_mcp_function内)

---

#### `compare_scrm_policies`
**機能**: 期待値最小化とCVaR最小化の2つの在庫方針を比較します。両方の最適化を実行し、在庫量、総費用、リスク指標を比較して推奨方針を提示します。

**入力パラメータ**:
```json
{
  "filename_suffix": "test_01",
  "h_cost": {
    "0,Retail_0001": 1.0,
    "1,Retail_0001": 1.0
  },
  "b_cost": {
    "0,Retail_0001": 10.0,
    "1,Retail_0001": 10.0
  },
  "disruption_prob": {
    "0": 0.1,
    "1": 0.1,
    "2": 0.05
  },
  "TTR": {
    "0": 2,
    "1": 3,
    "2": 2
  },
  "beta": 0.95,
  "K_max": 2
}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| filename_suffix | string | ✓ | 読み込むCSVファイル名のサフィックス |
| h_cost | object | ✓ | 在庫保管費用の辞書 |
| b_cost | object | ✓ | 品切れ費用の辞書 |
| disruption_prob | object | ✓ | 工場の途絶確率の辞書 |
| TTR | object | ✓ | 工場の回復時間の辞書 |
| beta | number | - | CVaR信頼水準（デフォルト: 0.95） |
| K_max | integer | - | 同時途絶する工場数の上限（デフォルト: 2） |

**出力**:
```json
{
  "status": "success",
  "expected_policy": {
    "optimal_inventory": {
      "0,Retail_0001": 150.5,
      "1,Retail_0001": 200.3
    },
    "total_cost": 1492.0,
    "expected_inventory_cost": 1492.0,
    "expected_backorder_cost": 0.0
  },
  "cvar_policy": {
    "optimal_inventory": {
      "0,Retail_0001": 180.2,
      "1,Retail_0001": 230.5
    },
    "cvar": 1650.5,
    "var": 1580.0,
    "expected_cost": 1520.0
  },
  "comparison": {
    "total_expected_inventory": 350.8,
    "total_cvar_inventory": 410.7,
    "inventory_increase": 59.9,
    "inventory_increase_pct": 17.1,
    "expected_total_cost": 1492.0,
    "cvar_total_cost": 1520.0,
    "cost_increase": 28.0,
    "cost_increase_pct": 1.88,
    "var": 1580.0,
    "cvar": 1650.5
  },
  "recommendation": "CVaR方針を推奨します。費用増加が小さく、リスク回避効果が高いです。",
  "message": "在庫方針の比較が完了しました"
}
```

**比較基準**:
- **在庫量**: CVaR方針は通常、期待値方針より多くの在庫を保持
- **費用**: 期待値方針の方が期待費用は低いが、リスクが高い
- **リスク指標**: CVaR/VaRは最悪ケースへの備えを示す

**推奨ロジック**:
- 費用増加率 < 5%: CVaR方針を推奨（コスト増加が小さく、リスク回避効果が高い）
- 費用増加率 5-15%: 状況に応じて選択（トレードオフを考慮）
- 費用増加率 > 15%: 期待値方針を推奨（CVaR方針の費用増加が大きすぎる）

**適用例**:
- 在庫方針の意思決定支援
- リスク許容度に応じた方針選択
- 経営層への提案資料作成

**実装**: `mcp_tools.py:5999` (execute_mcp_function内)

---

### SCRM分析の典型的なワークフロー

#### パターン1: ベンチマーク問題からの分析
```
1. generate_scrm_data: ベンチマーク問題からデータ生成
   ↓
2. save_scrm_data_to_csv: データをCSVに保存
   ↓
3. visualize_scrm_graph: ネットワーク構造を確認
   ↓
4. analyze_supply_chain_risk: リスク分析実行
   ↓
5. visualize_scrm_network: 分析結果を可視化
```

#### パターン2: 既存データからの再分析
```
1. load_scrm_data_from_csv: 保存済みデータを読み込み
   ↓
2. analyze_supply_chain_risk: リスク分析実行
   ↓
3. visualize_scrm_network: 分析結果を可視化
```

---

### 使用例

#### 例1: ベンチマーク問題01のリスク分析
```
ユーザー: ベンチマーク問題01を使ってサプライチェーンリスク分析を実行してください。工場数は3、各工場で2製品を生産できる設定にしてください。

アシスタント:
1. generate_scrm_data を実行（benchmark_id="01", n_plants=3, n_flex=2）
2. save_scrm_data_to_csv を実行（filename_suffix="bench01_3plants"）
3. analyze_supply_chain_risk を実行（filename_suffix="bench01_3plants"）
4. visualize_scrm_network を実行（filename_suffix="bench01_3plants"）

結果: TTS値の低いノード（リスクの高いノード）を特定し、可視化により一目で脆弱な箇所を把握できます。
```

#### 例2: 工場ネットワークの可視化
```
ユーザー: bench01_3plantsデータの工場ネットワークグラフを見せてください。

アシスタント:
visualize_scrm_graph を実行（filename_suffix="bench01_3plants", graph_type="plant"）

結果: 工場間の輸送リンクが可視化され、ネットワークの構造を確認できます。
```

---

### SCRM Tools実装関数

#### `execute_mcp_function(function_name: str, arguments: dict, user_id: int = None) -> dict`
**ファイル**: `mcp_tools.py:1401`

**SCRM関連の関数名**:
- `"generate_scrm_data"`
- `"save_scrm_data_to_csv"`
- `"load_scrm_data_from_csv"`
- `"visualize_scrm_graph"`
- `"analyze_supply_chain_risk"`
- `"visualize_scrm_network"`

**処理フロー**:
1. function_nameに応じて対応するSCRM実装関数を呼び出し
2. CSVファイルの読み書き（`./data/scrm/` ディレクトリ）
3. NetworkXを使ったグラフ操作
4. Plotlyを使った可視化
5. エラーハンドリング
6. 結果をdict形式で返す

---

### SCRM Tools cURL実行例

以下は、SCRM Toolsをcurlコマンドで直接実行する例です。

#### 前提条件

JWT認証トークンを取得する必要があります：

```bash
# 1. ログインしてトークンを取得
curl -X POST https://web-production-1ed39.up.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'

# レスポンス例:
# {"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer"}

# 2. トークンを環境変数に設定
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 例1: ベンチマーク問題01からSCRMデータ生成

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_scrm_data \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benchmark_id": "01",
    "n_plants": 3,
    "n_flex": 2,
    "seed": 1
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "benchmark_id": "01",
  "total_demand": 7460.0,
  "demand": {
    "(1, 'Retail_0002')": 0.0,
    "(2, 'Retail_0002')": 0.0
  },
  "network_info": {
    "num_plants": 9,
    "num_products": 8,
    "num_production_nodes": 18
  }
}
```

#### 例2: SCRMデータをCSVに保存

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/save_scrm_data_to_csv \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benchmark_id": "01",
    "filename_suffix": "test_01",
    "n_plants": 3,
    "n_flex": 2,
    "seed": 1
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "message": "SCRMデータをCSVファイルに保存しました",
  "files_created": [
    "./data/scrm/bom_test_01.csv",
    "./data/scrm/trans_test_01.csv",
    "./data/scrm/plnt_prod_test_01.csv",
    "./data/scrm/plnt_test_01.csv"
  ],
  "benchmark_id": "01",
  "filename_suffix": "test_01"
}
```

#### 例3: CSVからSCRMデータを読み込み

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/load_scrm_data_from_csv \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename_suffix": "test_01"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "message": "CSVファイル（test_01）からSCRMデータを読み込みました",
  "demand": {
    "(1, 'Retail_0002')": 0.0,
    "(2, 'Retail_0002')": 0.0
  },
  "num_plants": 9,
  "num_bom_nodes": 8,
  "num_production_nodes": 18
}
```

#### 例4: BOMグラフの可視化

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_scrm_graph \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename_suffix": "test_01",
    "graph_type": "bom",
    "title": "部品展開表（BOM）グラフ"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "visualization_id": "550e8400-e29b-41d4-a716-446655440005",
  "visualization_url": "/api/visualization/550e8400-e29b-41d4-a716-446655440005",
  "graph_type": "bom",
  "message": "部品展開表(BOM)グラフの可視化が完了しました"
}
```

可視化を表示するには：
```bash
# ブラウザで以下のURLを開く
open "https://web-production-1ed39.up.railway.app/api/visualization/550e8400-e29b-41d4-a716-446655440005"
```

#### 例5: 工場ネットワークグラフの可視化

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_scrm_graph \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename_suffix": "test_01",
    "graph_type": "plant",
    "title": "工場ネットワークグラフ",
    "node_size": 40,
    "node_color": "lightgreen"
  }'
```

#### 例6: 生産グラフの可視化

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_scrm_graph \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename_suffix": "test_01",
    "graph_type": "production",
    "title": "生産グラフ（工場×製品）"
  }'
```

#### 例7: サプライチェーンリスク分析（TTS計算）

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/analyze_supply_chain_risk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename_suffix": "test_01"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "filename_suffix": "test_01",
  "survival_times": {
    "(3, 'Manuf_0001')": 2.9486166,
    "(3, 'Manuf_0002')": 2.9486166,
    "(0, 'Retail_0001')": 0.0,
    "(0, 'Retail_0003')": 0.0
  },
  "statistics": {
    "mean_survival_time": 1.9657444,
    "median_survival_time": 2.9486166,
    "min_survival_time": 0.0,
    "max_survival_time": 2.9486166
  },
  "critical_nodes_top10": [
    {
      "node": "(0, 'Retail_0001')",
      "survival_time": 0.0
    },
    {
      "node": "(0, 'Retail_0003')",
      "survival_time": 0.0
    }
  ],
  "num_analyzed_nodes": 18,
  "message": "リスク分析が完了しました（18ノードを分析）"
}
```

#### 例8: リスク分析結果のネットワーク可視化

```bash
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_scrm_network \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename_suffix": "test_01"
  }'
```

**レスポンス例**:
```json
{
  "status": "success",
  "visualization_id": "f0cc89f4-fd25-4e1b-9e2b-f9233c70a655",
  "visualization_url": "/api/visualization/f0cc89f4-fd25-4e1b-9e2b-f9233c70a655",
  "filename_suffix": "test_01",
  "statistics": {
    "mean_survival_time": 1.9657444,
    "median_survival_time": 2.9486166,
    "min_survival_time": 0.0,
    "max_survival_time": 2.9486166
  },
  "message": "リスク分析ネットワークの可視化が完了しました（点の大きさ: 途絶時の生存期間, 色: パイプライン在庫）"
}
```

#### 典型的なワークフロー例

**フルワークフロー（データ生成→保存→分析→可視化）**:

```bash
# Step 1: データ生成
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/generate_scrm_data \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benchmark_id":"01","n_plants":3,"n_flex":2,"seed":1}'

# Step 2: CSV保存
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/save_scrm_data_to_csv \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benchmark_id":"01","filename_suffix":"my_analysis","n_plants":3,"n_flex":2,"seed":1}'

# Step 3: ネットワーク構造の可視化
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_scrm_graph \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename_suffix":"my_analysis","graph_type":"production","title":"生産ネットワーク"}'

# Step 4: リスク分析
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/analyze_supply_chain_risk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename_suffix":"my_analysis"}'

# Step 5: リスク分析結果の可視化
curl -X POST https://web-production-1ed39.up.railway.app/api/tools/visualize_scrm_network \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename_suffix":"my_analysis"}'
```

#### ローカル環境での実行例

ローカル開発環境（`ENVIRONMENT=local`）では、認証なしで実行できます：

```bash
# ローカル環境（認証不要）
curl -X POST http://localhost:8000/api/tools/generate_scrm_data \
  -H "Content-Type: application/json" \
  -d '{
    "benchmark_id": "01",
    "n_plants": 3,
    "n_flex": 2,
    "seed": 1
  }'
```

---

## 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `ENVIRONMENT` | `"production"` | 環境設定（"local" / "production"） |
| `DATABASE_URL` | `"sqlite:///./chat_app.db"` | データベース接続URL |
| `SECRET_KEY` | `"your-secret-key-change-this-in-production"` | JWT署名用秘密鍵 |
| `OPENAI_API_KEY` | `"not-needed"` | OpenAI APIキー |
| `OPENAI_BASE_URL` | `"http://localhost:1234/v1"` | OpenAI API URL（ローカルLLM対応） |
| `OPENAI_MODEL_NAME` | `"gpt-4o-mini"` | 使用モデル名 |
| `VISUALIZATION_OUTPUT_DIR` | `"/tmp/visualizations"` | 可視化ファイル保存先 |

---

### 環境変数設定例

#### ローカル開発環境
```bash
ENVIRONMENT=local
DATABASE_URL=sqlite:///./chat_app.db
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_MODEL_NAME=llama-3.1-8b-instruct
```

#### 本番環境（Railway）
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/dbname
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o-mini
SECRET_KEY=random-secure-key-here
VISUALIZATION_OUTPUT_DIR=/tmp/visualizations
```

---

## デプロイメント

### Railwayへのデプロイ

**設定ファイル**: `railway.json`, `nixpacks.toml`

**ビルドコマンド**:
```bash
pip install -r requirements.txt
```

**起動コマンド**:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**必須環境変数**:
- `DATABASE_URL` - PostgreSQL接続URL（Railwayが自動設定）
- `SECRET_KEY` - JWT署名用秘密鍵（手動設定）
- `OPENAI_API_KEY` - OpenAI APIキー（手動設定）

---

## まとめ

本アプリケーションは、FastAPI + OpenAI Function Calling + MCP Toolsを組み合わせた**在庫最適化専門AIチャットボット**です。

### 主要機能
- ✅ ユーザー認証（JWT）
- ✅ チャット履歴保存
- ✅ ストリーミングレスポンス
- ✅ 30種類以上の在庫最適化ツール
- ✅ インタラクティブな可視化（Plotly）
- ✅ Railway対応

### アーキテクチャの特徴
- **Function Calling**: LLMが自動的にツールを選択・実行
- **Two-Step Processing**: パラメータ変換を自動化
- **可視化キャッシュ**: ユーザーごとの可視化結果を管理
- **認証オプショナル**: ローカル環境では認証不要

### 技術スタック
- **バックエンド**: FastAPI + Uvicorn
- **データベース**: SQLAlchemy + PostgreSQL/SQLite
- **認証**: JWT (python-jose) + bcrypt
- **AI**: OpenAI API (Function Calling)
- **可視化**: Plotly
- **最適化**: PuLP, SciPy, NumPy

---

**ドキュメント作成日**: 2025-10-14
**バージョン**: 1.0

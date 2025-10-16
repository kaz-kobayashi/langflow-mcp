# MCP Tools Direct API 使用ガイド

## 概要

このAPIを使用すると、フロントエンドのチャット画面を経由せずに、30個以上の在庫最適化MCP Toolsを直接呼び出すことができます。

**重要**: すべてのAPIエンドポイントはJWT認証が必須です。

---

## 基本的な使い方

### 1. ユーザー登録とログイン

#### ユーザー登録

```bash
curl -X POST https://your-railway-app.railway.app/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "myusername",
    "password": "securepassword123"
  }'
```

**レスポンス**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### ログイン

```bash
curl -X POST https://your-railway-app.railway.app/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### 2. トークンを環境変数に保存

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. 利用可能なツール一覧を取得

```bash
curl -X GET https://your-railway-app.railway.app/api/tools \
  -H "Authorization: Bearer $TOKEN"
```

**レスポンス**:
```json
{
  "tools": [
    {
      "name": "calculate_eoq_raw",
      "description": "基本的な経済発注量（EOQ）を計算",
      "parameters": {...}
    },
    ...
  ],
  "total": 34,
  "user": "myusername"
}
```

---

## API使用例

### EOQ（経済発注量）計算

```bash
curl -X POST https://your-railway-app.railway.app/api/tools/calculate_eoq_raw \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "annual_demand": 15000,
    "order_cost": 500.0,
    "holding_cost_rate": 0.25,
    "unit_price": 12.0
  }'
```

**レスポンス**:
```json
{
  "status": "success",
  "optimal_order_quantity": 2236.07,
  "total_cost": 18.38,
  "annual_total_cost": 6708.20,
  "parameters": {
    "annual_demand": 15000,
    "daily_demand": 41.10,
    "order_cost": 500.0,
    "holding_cost_rate": 0.25,
    "daily_holding_cost": 0.0082,
    "unit_price": 12.0
  },
  "_meta": {
    "tool_name": "calculate_eoq_raw",
    "user_id": 3,
    "username": "myusername"
  }
}
```

### 安全在庫計算

```bash
curl -X POST https://your-railway-app.railway.app/api/tools/calculate_safety_stock \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mu": 100.0,
    "sigma": 20.0,
    "lead_time": 7,
    "service_level": 0.95
  }'
```

**レスポンス**:
```json
{
  "status": "success",
  "calculation_type": "安全在庫計算",
  "results": {
    "safety_stock": 87.04,
    "reorder_point": 787.04,
    "lead_time_demand_mean": 700.0,
    "lead_time_demand_std": 52.92,
    "z_value": 1.64
  },
  "service_level": {
    "target": 0.95,
    "percentage": "95.0%",
    "meaning": "需要の95.0%をカバー"
  },
  "input_parameters": {
    "daily_demand_mean": 100.0,
    "daily_demand_std": 20.0,
    "lead_time_days": 7
  },
  "_meta": {
    "tool_name": "calculate_safety_stock",
    "user_id": 3,
    "username": "myusername"
  }
}
```

### (Q,R)方策の最適化

```bash
curl -X POST https://your-railway-app.railway.app/api/tools/optimize_qr_policy \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mu": 100.0,
    "sigma": 20.0,
    "lead_time": 7,
    "holding_cost": 0.5,
    "stockout_cost": 50.0,
    "fixed_cost": 1000.0,
    "n_samples": 10,
    "n_periods": 100
  }'
```

### 需要予測

```bash
curl -X POST https://your-railway-app.railway.app/api/tools/forecast_demand \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "demand_history": [100, 105, 110, 108, 112, 115, 120],
    "forecast_periods": 7,
    "method": "exponential_smoothing",
    "visualize": false
  }'
```

---

## Python SDK

より使いやすいPython SDKも利用可能です。

### インストール

```bash
pip install requests
```

### SDK実装

`inventory_client.py`:

```python
import requests
from typing import Optional, Dict, Any, List

class InventoryOptimizationClient:
    """在庫最適化API クライアント"""

    def __init__(self, base_url: str, email: str = None, password: str = None, token: str = None):
        """
        クライアントを初期化

        Args:
            base_url: APIのベースURL (例: "https://your-app.railway.app")
            email: ユーザーのメールアドレス（新規登録/ログイン用）
            password: パスワード（新規登録/ログイン用）
            token: 既存のJWTトークン（持っている場合）
        """
        self.base_url = base_url.rstrip('/')
        self.token = token

        if not token and email and password:
            # トークンがない場合はログイン
            self.token = self.login(email, password)

    def register(self, email: str, username: str, password: str) -> str:
        """新規ユーザー登録"""
        response = requests.post(
            f"{self.base_url}/api/register",
            json={"email": email, "username": username, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token

    def login(self, email: str, password: str) -> str:
        """ログイン"""
        response = requests.post(
            f"{self.base_url}/api/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token

    def _call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """MCP Toolを呼び出す"""
        if not self.token:
            raise ValueError("トークンが設定されていません。登録またはログインしてください。")

        response = requests.post(
            f"{self.base_url}/api/tools/{tool_name}",
            json=kwargs,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        response.raise_for_status()
        return response.json()

    def list_tools(self) -> List[Dict[str, Any]]:
        """利用可能なツール一覧を取得"""
        if not self.token:
            raise ValueError("トークンが設定されていません。")

        response = requests.get(
            f"{self.base_url}/api/tools",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        response.raise_for_status()
        return response.json()["tools"]

    # EOQ計算
    def calculate_eoq(self, annual_demand: int, order_cost: float,
                     holding_cost_rate: float, unit_price: float,
                     visualize: bool = False) -> Dict[str, Any]:
        """基本EOQを計算"""
        return self._call_tool(
            "calculate_eoq_raw",
            annual_demand=annual_demand,
            order_cost=order_cost,
            holding_cost_rate=holding_cost_rate,
            unit_price=unit_price,
            visualize=visualize
        )

    # 安全在庫計算
    def calculate_safety_stock(self, mu: float, sigma: float, lead_time: int,
                               service_level: float) -> Dict[str, Any]:
        """安全在庫を計算"""
        return self._call_tool(
            "calculate_safety_stock",
            mu=mu,
            sigma=sigma,
            lead_time=lead_time,
            service_level=service_level
        )

    # (Q,R)方策
    def optimize_qr_policy(self, mu: float, sigma: float, lead_time: int,
                          holding_cost: float, stockout_cost: float,
                          fixed_cost: float, n_samples: int = 10,
                          n_periods: int = 100) -> Dict[str, Any]:
        """(Q,R)方策を最適化"""
        return self._call_tool(
            "optimize_qr_policy",
            mu=mu,
            sigma=sigma,
            lead_time=lead_time,
            holding_cost=holding_cost,
            stockout_cost=stockout_cost,
            fixed_cost=fixed_cost,
            n_samples=n_samples,
            n_periods=n_periods
        )

    # 需要予測
    def forecast_demand(self, demand_history: List[float], forecast_periods: int,
                       method: str = "exponential_smoothing",
                       visualize: bool = False) -> Dict[str, Any]:
        """需要を予測"""
        return self._call_tool(
            "forecast_demand",
            demand_history=demand_history,
            forecast_periods=forecast_periods,
            method=method,
            visualize=visualize
        )
```

### SDK使用例

```python
from inventory_client import InventoryOptimizationClient

# クライアントを初期化（自動ログイン）
client = InventoryOptimizationClient(
    base_url="https://your-railway-app.railway.app",
    email="user@example.com",
    password="securepassword123"
)

# または、既存のトークンを使用
# client = InventoryOptimizationClient(
#     base_url="https://your-railway-app.railway.app",
#     token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
# )

# 利用可能なツール一覧を取得
tools = client.list_tools()
print(f"利用可能なツール数: {len(tools)}")

# EOQ計算
eoq_result = client.calculate_eoq(
    annual_demand=15000,
    order_cost=500.0,
    holding_cost_rate=0.25,
    unit_price=12.0
)
print(f"最適発注量: {eoq_result['optimal_order_quantity']:.2f} units")
print(f"年間総コスト: {eoq_result['annual_total_cost']:.2f} 円")

# 安全在庫計算
safety_result = client.calculate_safety_stock(
    mu=100.0,
    sigma=20.0,
    lead_time=7,
    service_level=0.95
)
print(f"安全在庫: {safety_result['results']['safety_stock']:.2f} units")
print(f"発注点: {safety_result['results']['reorder_point']:.2f} units")

# (Q,R)方策の最適化
qr_result = client.optimize_qr_policy(
    mu=100.0,
    sigma=20.0,
    lead_time=7,
    holding_cost=0.5,
    stockout_cost=50.0,
    fixed_cost=1000.0,
    n_samples=10,
    n_periods=100
)
print(f"最適Q: {qr_result['optimal_Q']:.2f}")
print(f"最適R: {qr_result['optimal_R']:.2f}")

# 需要予測
forecast_result = client.forecast_demand(
    demand_history=[100, 105, 110, 108, 112, 115, 120],
    forecast_periods=7,
    method="exponential_smoothing"
)
print(f"予測値: {forecast_result['forecast']}")
```

---

## エラーハンドリング

### 認証エラー

```json
{
  "detail": "Not authenticated"
}
```

→ JWTトークンが無効または期限切れです。再ログインしてください。

### ツールが見つからない

```json
{
  "detail": "Tool 'invalid_tool_name' not found. Available tools: calculate_eoq_raw, ..."
}
```

→ ツール名が間違っています。`/api/tools`で利用可能なツール一覧を確認してください。

### パラメータエラー

```json
{
  "status": "error",
  "message": "必須パラメータが不足しています: service_level",
  "received_arguments": {...}
}
```

→ 必須パラメータが不足しています。エラーメッセージを確認して、不足しているパラメータを追加してください。

---

## 利用可能なツール一覧（全34種類）

### 1. EOQ（経済発注量）計算
- `calculate_eoq_raw` - 基本EOQ計算
- `calculate_eoq_incremental_discount_raw` - 増分数量割引EOQ
- `calculate_eoq_all_units_discount_raw` - 全単位数量割引EOQ
- `visualize_eoq` - EOQ可視化

### 2. 安全在庫計算
- `calculate_safety_stock` - 単一品目安全在庫計算
- `optimize_safety_stock_allocation` - マルチエシュロン安全在庫最適化（MESSA）
- `visualize_safety_stock_network` - 安全在庫ネットワーク可視化

### 3. (Q,R)方策（定量発注方式）
- `optimize_qr_policy` - (Q,R)方策の最適化
- `simulate_qr_policy` - (Q,R)方策のシミュレーション

### 4. (s,S)方策
- `optimize_ss_policy` - (s,S)方策の最適化
- `simulate_ss_policy` - (s,S)方策のシミュレーション

### 5. 基在庫方策
- `simulate_base_stock_policy` - 基在庫シミュレーション（需要配列指定）
- `base_stock_simulation_using_dist` - 基在庫シミュレーション（分布ベース）
- `calculate_base_stock_levels` - 基在庫レベル計算
- `simulate_network_base_stock` - ネットワーク基在庫シミュレーション

### 6. 定期発注方式
- `optimize_periodic_inventory` - 定期発注最適化（Adam/Momentum/SGD）
- `optimize_periodic_with_one_cycle` - Fit One Cycle学習率スケジューラ
- `find_optimal_learning_rate_periodic` - 最適学習率探索
- `visualize_periodic_optimization` - 定期発注最適化結果可視化

### 7. 需要分析・予測
- `forecast_demand` - 需要予測（移動平均/指数平滑/線形トレンド）
- `visualize_forecast` - 需要予測結果可視化
- `analyze_demand_pattern` - 需要パターン分析
- `find_best_distribution` - 最適確率分布フィッティング
- `visualize_demand_histogram` - 需要ヒストグラム可視化

### 8. その他
- `calculate_wagner_whitin` - Wagner-Whitinアルゴリズム
- `compare_inventory_policies` - 在庫方策比較
- `analyze_inventory_network` - 在庫ネットワーク分析
- `visualize_inventory_simulation` - 在庫シミュレーション可視化
- `visualize_simulation_trajectories` - シミュレーション軌道可視化
- `visualize_supply_chain_network` - サプライチェーンネットワーク可視化
- `compare_inventory_costs_visual` - 在庫コスト比較可視化
- `generate_sample_data` - サンプルデータ生成
- `visualize_last_optimization` - 直前の最適化結果可視化

---

## Swagger UI

自動生成されたAPIドキュメントは以下のURLで確認できます：

- **Swagger UI**: https://your-railway-app.railway.app/docs
- **ReDoc**: https://your-railway-app.railway.app/redoc

---

## 注意事項

1. **JWTトークンの有効期限**: トークンは7日間有効です。期限切れの場合は再ログインが必要です。

2. **レート制限**: 現在、レート制限は設定されていませんが、過度なリクエストは避けてください。

3. **可視化機能**: `visualize=true`を指定した場合、レスポンスに`visualization_id`が含まれます。可視化HTMLは`/api/visualization/{viz_id}`で取得できます。

4. **エラーハンドリング**: すべてのエラーは適切なHTTPステータスコードとエラーメッセージで返されます。

---

## サポート

問題が発生した場合は、以下の情報を含めてお問い合わせください：

- リクエストURL
- リクエストボディ
- レスポンス（エラーメッセージ含む）
- 期待される動作

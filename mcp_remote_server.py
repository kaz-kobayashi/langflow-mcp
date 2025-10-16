"""
MCP Server for Remote Supply Chain Inventory Optimization API
Railway上のFastAPIエンドポイントを使用するMCPサーバー
"""

from fastmcp import FastMCP
import os
from inventory_client import InventoryOptimizationClient

# 環境変数から設定を読み込み
API_BASE_URL = os.getenv("INVENTORY_API_URL", "https://web-production-1ed39.up.railway.app")
API_TOKEN = os.getenv("INVENTORY_API_TOKEN")  # 必須: JWTトークン

if not API_TOKEN:
    print("⚠️  警告: INVENTORY_API_TOKEN環境変数が設定されていません")
    print("設定方法:")
    print('  export INVENTORY_API_TOKEN="your-jwt-token-here"')
    print()
    print("トークンの取得方法:")
    print(f"  curl -X POST {API_BASE_URL}/api/login \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"email":"user@example.com","password":"your-password"}\'')
    print()

# APIクライアントを初期化
client = InventoryOptimizationClient(
    base_url=API_BASE_URL,
    token=API_TOKEN
)

# MCPサーバーの初期化
mcp = FastMCP("Remote Inventory Optimizer")


# =============================================================
# EOQ（経済発注量）計算
# =============================================================

@mcp.tool()
def calculate_eoq(
    annual_demand: int,
    order_cost: float,
    holding_cost_rate: float,
    unit_price: float,
    backorder_cost: float = 0.0,
    visualize: bool = False
) -> dict:
    """
    基本的な経済発注量（EOQ）を計算

    Args:
        annual_demand: 年間需要量（units/年）
        order_cost: 発注固定費用（円/回）
        holding_cost_rate: 在庫保管費率（0.25 = 25%）
        unit_price: 単価（円/unit）
        backorder_cost: バックオーダーコスト（円/unit/日、デフォルト0）
        visualize: 可視化するか（デフォルトFalse）

    Returns:
        dict: EOQ計算結果
    """
    return client.calculate_eoq(
        annual_demand=annual_demand,
        order_cost=order_cost,
        holding_cost_rate=holding_cost_rate,
        unit_price=unit_price,
        backorder_cost=backorder_cost,
        visualize=visualize
    )


@mcp.tool()
def calculate_eoq_with_discount(
    annual_demand: int,
    order_cost: float,
    holding_cost_rate: float,
    price_table: list,
    discount_type: str = "all_units",
    visualize: bool = False
) -> dict:
    """
    数量割引を考慮したEOQを計算

    Args:
        annual_demand: 年間需要量（units/年）
        order_cost: 発注固定費用（円/回）
        holding_cost_rate: 在庫保管費率（0.25 = 25%）
        price_table: 単価テーブル [{"quantity": 0, "price": 12.0}, ...]
        discount_type: 割引タイプ（"all_units" or "incremental"）
        visualize: 可視化するか

    Returns:
        dict: EOQ計算結果
    """
    return client.calculate_eoq_with_discount(
        annual_demand=annual_demand,
        order_cost=order_cost,
        holding_cost_rate=holding_cost_rate,
        price_table=price_table,
        discount_type=discount_type,
        visualize=visualize
    )


# =============================================================
# 安全在庫計算
# =============================================================

@mcp.tool()
def calculate_safety_stock(
    mu: float,
    sigma: float,
    lead_time: int,
    service_level: float
) -> dict:
    """
    安全在庫を計算

    Args:
        mu: 平均需要量（units/日）
        sigma: 需要の標準偏差
        lead_time: リードタイム（日）
        service_level: 目標サービスレベル（0.95 = 95%）

    Returns:
        dict: 安全在庫計算結果
    """
    return client.calculate_safety_stock(
        mu=mu,
        sigma=sigma,
        lead_time=lead_time,
        service_level=service_level
    )


# =============================================================
# (Q,R)方策
# =============================================================

@mcp.tool()
def optimize_qr_policy(
    mu: float,
    sigma: float,
    lead_time: int,
    holding_cost: float,
    stockout_cost: float,
    fixed_cost: float,
    n_samples: int = 10,
    n_periods: int = 100
) -> dict:
    """
    (Q,R)方策を最適化

    Args:
        mu: 1日あたりの平均需要量（units/日）
        sigma: 需要の標準偏差
        lead_time: リードタイム（日）
        holding_cost: 在庫保管費用（円/unit/日）
        stockout_cost: 品切れ費用（円/unit）
        fixed_cost: 固定発注費用（円/回）
        n_samples: シミュレーションサンプル数（デフォルト10）
        n_periods: シミュレーション期間（日、デフォルト100）

    Returns:
        dict: 最適化結果
    """
    return client.optimize_qr_policy(
        mu=mu,
        sigma=sigma,
        lead_time=lead_time,
        holding_cost=holding_cost,
        stockout_cost=stockout_cost,
        fixed_cost=fixed_cost,
        n_samples=n_samples,
        n_periods=n_periods
    )


@mcp.tool()
def simulate_qr_policy(
    Q: float,
    R: float,
    mu: float,
    sigma: float,
    lead_time: int,
    holding_cost: float,
    stockout_cost: float,
    fixed_cost: float,
    n_samples: int = 100,
    n_periods: int = 200
) -> dict:
    """
    (Q,R)方策のシミュレーション

    Args:
        Q: 発注量（units）
        R: 発注点（units）
        mu: 1日あたりの平均需要量（units/日）
        sigma: 需要の標準偏差
        lead_time: リードタイム（日）
        holding_cost: 在庫保管費用（円/unit/日）
        stockout_cost: 品切れ費用（円/unit）
        fixed_cost: 固定発注費用（円/回）
        n_samples: シミュレーションサンプル数（デフォルト100）
        n_periods: シミュレーション期間（日、デフォルト200）

    Returns:
        dict: シミュレーション結果
    """
    return client.simulate_qr_policy(
        Q=Q,
        R=R,
        mu=mu,
        sigma=sigma,
        lead_time=lead_time,
        holding_cost=holding_cost,
        stockout_cost=stockout_cost,
        fixed_cost=fixed_cost,
        n_samples=n_samples,
        n_periods=n_periods
    )


# =============================================================
# (s,S)方策
# =============================================================

@mcp.tool()
def optimize_ss_policy(
    mu: float,
    sigma: float,
    lead_time: int,
    holding_cost: float,
    stockout_cost: float,
    fixed_cost: float,
    n_samples: int = 10,
    n_periods: int = 100
) -> dict:
    """
    (s,S)方策を最適化

    Args:
        mu: 1日あたりの平均需要量（units/日）
        sigma: 需要の標準偏差
        lead_time: リードタイム（日）
        holding_cost: 在庫保管費用（円/unit/日）
        stockout_cost: 品切れ費用（円/unit）
        fixed_cost: 固定発注費用（円/回）
        n_samples: シミュレーションサンプル数（デフォルト10）
        n_periods: シミュレーション期間（日、デフォルト100）

    Returns:
        dict: 最適化結果
    """
    return client.optimize_ss_policy(
        mu=mu,
        sigma=sigma,
        lead_time=lead_time,
        holding_cost=holding_cost,
        stockout_cost=stockout_cost,
        fixed_cost=fixed_cost,
        n_samples=n_samples,
        n_periods=n_periods
    )


# =============================================================
# 需要予測
# =============================================================

@mcp.tool()
def forecast_demand(
    demand_history: list,
    forecast_periods: int,
    method: str = "exponential_smoothing",
    confidence_level: float = 0.95,
    visualize: bool = False
) -> dict:
    """
    需要を予測

    Args:
        demand_history: 過去の需要データ
        forecast_periods: 予測する期間数
        method: 予測手法（"moving_average", "exponential_smoothing", "linear_trend"）
        confidence_level: 信頼水準（0.95 = 95%）
        visualize: 可視化するか

    Returns:
        dict: 予測結果
    """
    return client.forecast_demand(
        demand_history=demand_history,
        forecast_periods=forecast_periods,
        method=method,
        confidence_level=confidence_level,
        visualize=visualize
    )


# =============================================================
# 需要分析
# =============================================================

@mcp.tool()
def analyze_demand_pattern(demand: list) -> dict:
    """
    需要パターンを分析

    Args:
        demand: 需要データ

    Returns:
        dict: 分析結果
    """
    return client.analyze_demand_pattern(demand=demand)


@mcp.tool()
def find_best_distribution(demand: list) -> dict:
    """
    最適な確率分布をフィッティング

    Args:
        demand: 需要データ

    Returns:
        dict: フィッティング結果
    """
    return client.find_best_distribution(demand=demand)


# =============================================================
# ツール一覧取得
# =============================================================

@mcp.tool()
def list_available_tools() -> dict:
    """
    利用可能なツール一覧を取得

    Returns:
        dict: ツール情報のリスト
    """
    try:
        tools = client.list_tools()
        return {
            "status": "success",
            "total_tools": len(tools),
            "tools": [{"name": tool["name"], "description": tool["description"]} for tool in tools]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    # MCPサーバー起動
    print(f"🚀 Starting Remote Inventory Optimizer MCP Server")
    print(f"📍 API URL: {API_BASE_URL}")
    print(f"🔑 Token: {'✓ Set' if API_TOKEN else '✗ Not Set'}")
    print()
    mcp.run()

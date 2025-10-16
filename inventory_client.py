"""
在庫最適化API Python SDK

使用例:
    from inventory_client import InventoryOptimizationClient

    # クライアントを初期化
    client = InventoryOptimizationClient(
        base_url="https://your-railway-app.railway.app",
        email="user@example.com",
        password="password123"
    )

    # EOQ計算
    result = client.calculate_eoq(
        annual_demand=15000,
        order_cost=500.0,
        holding_cost_rate=0.25,
        unit_price=12.0
    )
    print(f"最適発注量: {result['optimal_order_quantity']}")
"""

import requests
from typing import Optional, Dict, Any, List


class InventoryOptimizationClient:
    """在庫最適化API クライアント"""

    def __init__(
        self,
        base_url: str,
        email: str = None,
        password: str = None,
        token: str = None
    ):
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
        """
        新規ユーザー登録

        Args:
            email: メールアドレス
            username: ユーザー名
            password: パスワード

        Returns:
            JWTアクセストークン

        Raises:
            requests.HTTPError: 登録に失敗した場合
        """
        response = requests.post(
            f"{self.base_url}/api/register",
            json={"email": email, "username": username, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token

    def login(self, email: str, password: str) -> str:
        """
        ログイン

        Args:
            email: メールアドレス
            password: パスワード

        Returns:
            JWTアクセストークン

        Raises:
            requests.HTTPError: ログインに失敗した場合
        """
        response = requests.post(
            f"{self.base_url}/api/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token

    def _call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        MCP Toolを呼び出す

        Args:
            tool_name: ツール名
            **kwargs: ツールのパラメータ

        Returns:
            ツールの実行結果

        Raises:
            ValueError: トークンが設定されていない場合
            requests.HTTPError: API呼び出しに失敗した場合
        """
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
        """
        利用可能なツール一覧を取得

        Returns:
            ツール情報のリスト

        Raises:
            ValueError: トークンが設定されていない場合
            requests.HTTPError: API呼び出しに失敗した場合
        """
        if not self.token:
            raise ValueError("トークンが設定されていません。")

        response = requests.get(
            f"{self.base_url}/api/tools",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        response.raise_for_status()
        return response.json()["tools"]

    # =============================================================
    # EOQ計算
    # =============================================================

    def calculate_eoq(
        self,
        annual_demand: int,
        order_cost: float,
        holding_cost_rate: float,
        unit_price: float,
        backorder_cost: float = 0.0,
        visualize: bool = False
    ) -> Dict[str, Any]:
        """
        基本EOQを計算

        Args:
            annual_demand: 年間需要量（units/年）
            order_cost: 発注固定費用（円/回）
            holding_cost_rate: 在庫保管費率（0.25 = 25%）
            unit_price: 単価（円/unit）
            backorder_cost: バックオーダーコスト（円/unit/日）
            visualize: 可視化するか

        Returns:
            計算結果
        """
        return self._call_tool(
            "calculate_eoq_raw",
            annual_demand=annual_demand,
            order_cost=order_cost,
            holding_cost_rate=holding_cost_rate,
            unit_price=unit_price,
            backorder_cost=backorder_cost,
            visualize=visualize
        )

    def calculate_eoq_with_discount(
        self,
        annual_demand: int,
        order_cost: float,
        holding_cost_rate: float,
        price_table: List[Dict[str, float]],
        discount_type: str = "all_units",
        visualize: bool = False
    ) -> Dict[str, Any]:
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
            計算結果
        """
        tool_name = (
            "calculate_eoq_all_units_discount_raw"
            if discount_type == "all_units"
            else "calculate_eoq_incremental_discount_raw"
        )
        return self._call_tool(
            tool_name,
            annual_demand=annual_demand,
            order_cost=order_cost,
            holding_cost_rate=holding_cost_rate,
            price_table=price_table,
            visualize=visualize
        )

    # =============================================================
    # 安全在庫計算
    # =============================================================

    def calculate_safety_stock(
        self,
        mu: float,
        sigma: float,
        lead_time: int,
        service_level: float
    ) -> Dict[str, Any]:
        """
        安全在庫を計算

        Args:
            mu: 平均需要量（units/日）
            sigma: 需要の標準偏差
            lead_time: リードタイム（日）
            service_level: 目標サービスレベル（0.95 = 95%）

        Returns:
            計算結果
        """
        return self._call_tool(
            "calculate_safety_stock",
            mu=mu,
            sigma=sigma,
            lead_time=lead_time,
            service_level=service_level
        )

    # =============================================================
    # (Q,R)方策
    # =============================================================

    def optimize_qr_policy(
        self,
        mu: float,
        sigma: float,
        lead_time: int,
        holding_cost: float,
        stockout_cost: float,
        fixed_cost: float,
        n_samples: int = 10,
        n_periods: int = 100
    ) -> Dict[str, Any]:
        """
        (Q,R)方策を最適化

        Args:
            mu: 1日あたりの平均需要量（units/日）
            sigma: 需要の標準偏差
            lead_time: リードタイム（日）
            holding_cost: 在庫保管費用（円/unit/日）
            stockout_cost: 品切れ費用（円/unit）
            fixed_cost: 固定発注費用（円/回）
            n_samples: シミュレーションサンプル数
            n_periods: シミュレーション期間（日）

        Returns:
            最適化結果
        """
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

    def simulate_qr_policy(
        self,
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
    ) -> Dict[str, Any]:
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
            n_samples: シミュレーションサンプル数
            n_periods: シミュレーション期間（日）

        Returns:
            シミュレーション結果
        """
        return self._call_tool(
            "simulate_qr_policy",
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

    def optimize_ss_policy(
        self,
        mu: float,
        sigma: float,
        lead_time: int,
        holding_cost: float,
        stockout_cost: float,
        fixed_cost: float,
        n_samples: int = 10,
        n_periods: int = 100
    ) -> Dict[str, Any]:
        """
        (s,S)方策を最適化

        Args:
            mu: 1日あたりの平均需要量（units/日）
            sigma: 需要の標準偏差
            lead_time: リードタイム（日）
            holding_cost: 在庫保管費用（円/unit/日）
            stockout_cost: 品切れ費用（円/unit）
            fixed_cost: 固定発注費用（円/回）
            n_samples: シミュレーションサンプル数
            n_periods: シミュレーション期間（日）

        Returns:
            最適化結果
        """
        return self._call_tool(
            "optimize_ss_policy",
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

    def forecast_demand(
        self,
        demand_history: List[float],
        forecast_periods: int,
        method: str = "exponential_smoothing",
        confidence_level: float = 0.95,
        visualize: bool = False
    ) -> Dict[str, Any]:
        """
        需要を予測

        Args:
            demand_history: 過去の需要データ
            forecast_periods: 予測する期間数
            method: 予測手法（"moving_average", "exponential_smoothing", "linear_trend"）
            confidence_level: 信頼水準（0.95 = 95%）
            visualize: 可視化するか

        Returns:
            予測結果
        """
        return self._call_tool(
            "forecast_demand",
            demand_history=demand_history,
            forecast_periods=forecast_periods,
            method=method,
            confidence_level=confidence_level,
            visualize=visualize
        )

    # =============================================================
    # 需要分析
    # =============================================================

    def analyze_demand_pattern(self, demand: List[float]) -> Dict[str, Any]:
        """
        需要パターンを分析

        Args:
            demand: 需要データ

        Returns:
            分析結果
        """
        return self._call_tool(
            "analyze_demand_pattern",
            demand=demand
        )

    def find_best_distribution(self, demand: List[float]) -> Dict[str, Any]:
        """
        最適な確率分布をフィッティング

        Args:
            demand: 需要データ

        Returns:
            フィッティング結果
        """
        return self._call_tool(
            "find_best_distribution",
            demand=demand
        )


# 使用例
if __name__ == "__main__":
    import json

    # クライアントを初期化（ログイン）
    client = InventoryOptimizationClient(
        base_url="http://localhost:8000",
        email="testapi@example.com",
        password="testpass123"
    )

    # 利用可能なツール一覧を取得
    print("=== 利用可能なツール ===")
    tools = client.list_tools()
    print(f"ツール数: {len(tools)}")
    print(f"最初の3つ: {[t['name'] for t in tools[:3]]}\n")

    # EOQ計算
    print("=== EOQ計算 ===")
    eoq_result = client.calculate_eoq(
        annual_demand=15000,
        order_cost=500.0,
        holding_cost_rate=0.25,
        unit_price=12.0
    )
    print(f"最適発注量: {eoq_result['optimal_order_quantity']:.2f} units")
    print(f"年間総コスト: {eoq_result['annual_total_cost']:.2f} 円\n")

    # 安全在庫計算
    print("=== 安全在庫計算 ===")
    safety_result = client.calculate_safety_stock(
        mu=100.0,
        sigma=20.0,
        lead_time=7,
        service_level=0.95
    )
    print(f"安全在庫: {safety_result['results']['safety_stock']:.2f} units")
    print(f"発注点: {safety_result['results']['reorder_point']:.2f} units\n")

    # 需要予測
    print("=== 需要予測 ===")
    forecast_result = client.forecast_demand(
        demand_history=[100, 105, 110, 108, 112, 115, 120],
        forecast_periods=7,
        method="exponential_smoothing"
    )
    print(f"予測値: {forecast_result['forecast'][:3]}... (最初の3期間)")

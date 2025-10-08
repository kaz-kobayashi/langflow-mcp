"""
Phase 9: EOQ (Economic Order Quantity) Calculator
経済発注量計算機能

機能:
- 基本EOQ計算（バックオーダー対応含む）
- 増分数量割引対応EOQ
- 全単位数量割引対応EOQ
- EOQ分析の可視化
"""

import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from scmopt2.optinv import eoq


def calculate_eoq(
    K: float,
    d: float,
    h: float,
    b: float = None
) -> dict:
    """
    基本的な経済発注量（EOQ）を計算

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）- Noneの場合はバックオーダーなし

    Returns:
        dict: {
            'optimal_order_quantity': 最適発注量,
            'optimal_reorder_point': 最適発注点（またはSSの平方根）,
            'parameters': パラメータ情報
        }
    """
    Q_star, r_or_ss = eoq(K=K, d=d, h=h, b=b, r=0, c=0, theta=0, discount=None)

    return {
        'optimal_order_quantity': float(Q_star),
        'optimal_reorder_point_or_safety_stock_sqrt': float(r_or_ss),
        'parameters': {
            'fixed_order_cost': K,
            'average_demand': d,
            'holding_cost': h,
            'stockout_cost': b if b is not None else 'N/A',
            'backorder_allowed': b is not None
        }
    }


def calculate_eoq_with_incremental_discount(
    K: float,
    d: float,
    h: float,
    b: float,
    r: float,
    unit_costs: list,
    quantity_breaks: list
) -> dict:
    """
    増分数量割引対応EOQ計算

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）
        r: 割引率
        unit_costs: 各価格帯の単価リスト [c0, c1, c2, ...]
        quantity_breaks: 各価格帯の最小発注量 [θ0, θ1, θ2, ...]

    Returns:
        dict: {
            'optimal_order_quantity': 最適発注量,
            'total_cost': 総コスト,
            'selected_price_tier': 選択された価格帯のインデックス,
            'parameters': パラメータ情報
        }
    """
    Q_star, total_cost = eoq(
        K=K, d=d, h=h, b=b, r=r,
        c=unit_costs, theta=quantity_breaks,
        discount="incremental"
    )

    # どの価格帯が選択されたか判定
    selected_tier = 0
    for i, theta in enumerate(quantity_breaks):
        if Q_star >= theta:
            selected_tier = i

    return {
        'optimal_order_quantity': float(Q_star),
        'total_cost': float(total_cost),
        'selected_price_tier': selected_tier,
        'selected_unit_cost': unit_costs[selected_tier],
        'parameters': {
            'fixed_order_cost': K,
            'average_demand': d,
            'holding_cost': h,
            'stockout_cost': b,
            'discount_rate': r,
            'unit_costs': unit_costs,
            'quantity_breaks': quantity_breaks
        }
    }


def calculate_eoq_with_all_units_discount(
    K: float,
    d: float,
    h: float,
    b: float,
    r: float,
    unit_costs: list,
    quantity_breaks: list
) -> dict:
    """
    全単位数量割引対応EOQ計算

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）
        r: 割引率
        unit_costs: 各価格帯の単価リスト [c0, c1, c2, ...]
        quantity_breaks: 各価格帯の最小発注量 [θ0, θ1, θ2, ...]

    Returns:
        dict: {
            'optimal_order_quantity': 最適発注量,
            'total_cost': 総コスト,
            'selected_price_tier': 選択された価格帯のインデックス,
            'parameters': パラメータ情報
        }
    """
    Q_star, total_cost = eoq(
        K=K, d=d, h=h, b=b, r=r,
        c=unit_costs, theta=quantity_breaks,
        discount="all"
    )

    # どの価格帯が選択されたか判定
    selected_tier = 0
    for i, theta in enumerate(quantity_breaks):
        if Q_star >= theta:
            selected_tier = i

    return {
        'optimal_order_quantity': float(Q_star),
        'total_cost': float(total_cost),
        'selected_price_tier': selected_tier,
        'selected_unit_cost': unit_costs[selected_tier],
        'parameters': {
            'fixed_order_cost': K,
            'average_demand': d,
            'holding_cost': h,
            'stockout_cost': b,
            'discount_rate': r,
            'unit_costs': unit_costs,
            'quantity_breaks': quantity_breaks
        }
    }


def compare_eoq_scenarios(scenarios: list) -> dict:
    """
    複数のEOQシナリオを比較

    Args:
        scenarios: シナリオのリスト。各シナリオは以下の形式:
            {
                'name': シナリオ名,
                'type': 'basic' | 'incremental' | 'all_units',
                'params': パラメータdict
            }

    Returns:
        dict: 比較結果
    """
    results = []

    for scenario in scenarios:
        name = scenario['name']
        scenario_type = scenario['type']
        params = scenario['params']

        if scenario_type == 'basic':
            result = calculate_eoq(**params)
        elif scenario_type == 'incremental':
            result = calculate_eoq_with_incremental_discount(**params)
        elif scenario_type == 'all_units':
            result = calculate_eoq_with_all_units_discount(**params)
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")

        results.append({
            'name': name,
            'type': scenario_type,
            'result': result
        })

    return {
        'scenarios': results,
        'comparison_summary': {
            'best_scenario_by_cost': min(
                [r for r in results if 'total_cost' in r['result']],
                key=lambda x: x['result']['total_cost']
            )['name'] if any('total_cost' in r['result'] for r in results) else 'N/A'
        }
    }


def visualize_eoq_analysis(
    K: float,
    d: float,
    h: float,
    b: float = None,
    Q_range: tuple = None
) -> go.Figure:
    """
    EOQ分析を可視化（総コスト曲線）

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）
        Q_range: 発注量の範囲 (min, max)。Noneの場合は自動設定

    Returns:
        plotly Figure: 総コスト曲線のグラフ
    """
    # 最適発注量を計算
    result = calculate_eoq(K=K, d=d, h=h, b=b)
    Q_star = result['optimal_order_quantity']

    # 発注量の範囲を設定
    if Q_range is None:
        Q_min = max(1, Q_star * 0.3)
        Q_max = Q_star * 2.0
    else:
        Q_min, Q_max = Q_range

    Q_values = np.linspace(Q_min, Q_max, 200)

    # オメガ（サービスレベルパラメータ）の計算
    if b is None:
        omega = 1.0
    else:
        omega = b / (b + h)

    # 各コスト成分を計算
    ordering_cost = K * d / Q_values
    holding_cost = h * omega * Q_values / 2
    total_cost = ordering_cost + holding_cost

    # グラフを作成
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=["EOQ分析: 総コスト曲線"]
    )

    # 発注費用
    fig.add_trace(go.Scatter(
        x=Q_values,
        y=ordering_cost,
        mode='lines',
        name='発注費用',
        line=dict(color='blue', dash='dash')
    ))

    # 在庫保管費用
    fig.add_trace(go.Scatter(
        x=Q_values,
        y=holding_cost,
        mode='lines',
        name='在庫保管費用',
        line=dict(color='green', dash='dash')
    ))

    # 総コスト
    fig.add_trace(go.Scatter(
        x=Q_values,
        y=total_cost,
        mode='lines',
        name='総コスト',
        line=dict(color='red', width=3)
    ))

    # 最適発注量を示す垂直線
    fig.add_vline(
        x=Q_star,
        line_dash="dot",
        line_color="black",
        annotation_text=f"最適発注量 Q*={Q_star:.1f}",
        annotation_position="top"
    )

    # レイアウト設定
    fig.update_layout(
        title=f"EOQ分析 (K={K}, d={d}, h={h}, b={b})",
        xaxis_title="発注量 Q (units)",
        yaxis_title="コスト (円/日)",
        hovermode='x unified',
        showlegend=True,
        height=500
    )

    return fig


def visualize_eoq_with_discount(
    K: float,
    d: float,
    h: float,
    b: float,
    r: float,
    unit_costs: list,
    quantity_breaks: list,
    discount_type: str = "all"
) -> go.Figure:
    """
    数量割引対応EOQの可視化

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）
        r: 割引率
        unit_costs: 各価格帯の単価リスト [c0, c1, c2, ...]
        quantity_breaks: 各価格帯の最小発注量 [θ0, θ1, θ2, ...]
        discount_type: 'incremental' または 'all'

    Returns:
        plotly Figure: 数量割引を考慮した総コスト曲線
    """
    # 最適解を計算
    if discount_type == "incremental":
        result = calculate_eoq_with_incremental_discount(
            K=K, d=d, h=h, b=b, r=r,
            unit_costs=unit_costs, quantity_breaks=quantity_breaks
        )
    else:
        result = calculate_eoq_with_all_units_discount(
            K=K, d=d, h=h, b=b, r=r,
            unit_costs=unit_costs, quantity_breaks=quantity_breaks
        )

    Q_star = result['optimal_order_quantity']

    # 発注量の範囲
    Q_min = 1
    Q_max = max(quantity_breaks[-1] * 1.5, Q_star * 1.5)
    Q_values = np.linspace(Q_min, Q_max, 500)

    omega = b / (b + h)

    # 各価格帯での総コストを計算
    fig = go.Figure()

    for i, (c, theta) in enumerate(zip(unit_costs, quantity_breaks)):
        # この価格帯が適用される範囲
        if i < len(quantity_breaks) - 1:
            Q_range = Q_values[(Q_values >= theta) & (Q_values < quantity_breaks[i+1])]
        else:
            Q_range = Q_values[Q_values >= theta]

        if len(Q_range) > 0:
            if discount_type == "incremental":
                Kj = K + (unit_costs[0] - c) * theta
                total_cost = d * c + K * d / Q_range + (h + r * c) * omega * Q_range / 2
            else:  # all units
                total_cost = d * c + K * d / Q_range + (h + r * c) * Q_range / 2

            fig.add_trace(go.Scatter(
                x=Q_range,
                y=total_cost,
                mode='lines',
                name=f'価格帯{i+1}: c={c}, θ≥{theta}',
                line=dict(width=2)
            ))

    # 最適発注量を示す
    fig.add_vline(
        x=Q_star,
        line_dash="dot",
        line_color="black",
        annotation_text=f"最適 Q*={Q_star:.1f}",
        annotation_position="top"
    )

    fig.update_layout(
        title=f"数量割引EOQ分析 ({discount_type})",
        xaxis_title="発注量 Q (units)",
        yaxis_title="総コスト (円/日)",
        hovermode='x unified',
        showlegend=True,
        height=500
    )

    return fig


if __name__ == "__main__":
    # 基本EOQのテスト
    print("=== 基本EOQ計算 ===")
    result = calculate_eoq(K=100, d=10, h=1, b=10)
    print(f"最適発注量: {result['optimal_order_quantity']:.2f}")
    print(f"パラメータ: {result['parameters']}")

    # 可視化のテスト
    print("\n=== EOQ可視化 ===")
    fig = visualize_eoq_analysis(K=100, d=10, h=1, b=10)
    fig.write_html("/tmp/eoq_basic.html")
    print("グラフを /tmp/eoq_basic.html に保存")

    # 数量割引EOQのテスト
    print("\n=== 全単位数量割引EOQ ===")
    result = calculate_eoq_with_all_units_discount(
        K=100, d=1000, h=2, b=100, r=0.1,
        unit_costs=[10, 9, 8],
        quantity_breaks=[0, 100, 200]
    )
    print(f"最適発注量: {result['optimal_order_quantity']:.2f}")
    print(f"総コスト: {result['total_cost']:.2f}")
    print(f"選択された価格帯: {result['selected_price_tier']} (単価={result['selected_unit_cost']})")

    # 数量割引の可視化
    fig = visualize_eoq_with_discount(
        K=100, d=1000, h=2, b=100, r=0.1,
        unit_costs=[10, 9, 8],
        quantity_breaks=[0, 100, 200],
        discount_type="all"
    )
    fig.write_html("/tmp/eoq_discount.html")
    print("グラフを /tmp/eoq_discount.html に保存")

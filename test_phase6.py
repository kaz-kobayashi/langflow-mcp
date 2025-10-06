"""
Phase 6: 需要予測機能のテスト
"""

from mcp_tools import execute_mcp_function
import numpy as np

print("=" * 60)
print("Test 1: forecast_demand (指数平滑法)")
print("=" * 60)

# 上昇トレンドのある需要データ
np.random.seed(42)
demand_with_trend = [10 + 0.5*i + np.random.normal(0, 2) for i in range(20)]

result = execute_mcp_function(
    "forecast_demand",
    {
        "demand_history": demand_with_trend,
        "forecast_periods": 7,
        "method": "exponential_smoothing",
        "alpha": 0.3
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"手法: {result['method_info']['method']}")
    print(f"予測期間: {result['forecast_periods']}")
    print(f"予測値: {[f'{x:.2f}' for x in result['forecast']]}")
    print(f"信頼区間 下限: {[f'{x:.2f}' for x in result['lower_bound']]}")
    print(f"信頼区間 上限: {[f'{x:.2f}' for x in result['upper_bound']]}")
    print(f"過去データ平均: {result['historical_stats']['mean']:.2f}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 2: forecast_demand (移動平均法)")
print("=" * 60)

# 定常的な需要データ
demand_stationary = [10, 12, 8, 15, 11, 9, 13, 10, 14, 11, 12, 10, 9, 11, 13]

result = execute_mcp_function(
    "forecast_demand",
    {
        "demand_history": demand_stationary,
        "forecast_periods": 5,
        "method": "moving_average",
        "window": 5
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"手法: {result['method_info']['method']}")
    print(f"ウィンドウ: {result['method_info'].get('window', 'N/A')}")
    print(f"予測値: {[f'{x:.2f}' for x in result['forecast']]}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 3: forecast_demand (線形トレンド法)")
print("=" * 60)

# 明確なトレンドのある需要データ
demand_strong_trend = [5 + 2*i + np.random.normal(0, 1) for i in range(15)]

result = execute_mcp_function(
    "forecast_demand",
    {
        "demand_history": demand_strong_trend,
        "forecast_periods": 10,
        "method": "linear_trend",
        "confidence_level": 0.90
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"手法: {result['method_info']['method']}")
    print(f"トレンド係数: {result['method_info'].get('trend', 'N/A')}")
    print(f"切片: {result['method_info'].get('intercept', 'N/A')}")
    print(f"予測値: {[f'{x:.2f}' for x in result['forecast']]}")
    print(f"信頼水準: {result['confidence_level']*100:.0f}%")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 4: visualize_forecast (指数平滑法)")
print("=" * 60)

# 季節性のような需要データ
demand_seasonal = [10, 15, 12, 18, 11, 16, 13, 19, 12, 17, 14, 20, 13, 18, 15, 21]

result = execute_mcp_function(
    "visualize_forecast",
    {
        "demand_history": demand_seasonal,
        "forecast_periods": 6,
        "method": "exponential_smoothing",
        "alpha": 0.4
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"可視化タイプ: {result['visualization_type']}")
    print(f"手法: {result['method']}")
    print(f"予測期間: {result['forecast_summary']['forecast_periods']}")
    print(f"予測平均: {result['forecast_summary']['average_forecast']:.2f}")
    print(f"過去データ平均: {result['forecast_summary']['historical_average']:.2f}")
    print(f"Visualization ID: {result['visualization_id']}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 5: visualize_forecast (線形トレンド法)")
print("=" * 60)

result = execute_mcp_function(
    "visualize_forecast",
    {
        "demand_history": demand_with_trend,
        "forecast_periods": 7,
        "method": "linear_trend"
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"手法: {result['method']}")
    print(f"Visualization ID: {result['visualization_id']}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 6: エラーケース（データ不足）")
print("=" * 60)

result = execute_mcp_function(
    "forecast_demand",
    {
        "demand_history": [10],  # 1期間のみ
        "forecast_periods": 5
    },
    user_id=1
)

print(f"Status: {result['status']}")
print(f"Message: {result['message']}")

print("\n" + "=" * 60)
print("All Phase 6 tests completed!")
print("=" * 60)

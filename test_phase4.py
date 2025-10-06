"""
Phase 4の3つの新機能をテストするスクリプト
"""
from mcp_tools import execute_mcp_function
import numpy as np

# Test 1: find_best_distribution (正規分布に近いデータ)
print("=" * 60)
print("Test 1: find_best_distribution (正規分布)")
print("=" * 60)
# 正規分布に従う需要データを生成
np.random.seed(42)
normal_demand = list(np.random.normal(10, 2, 100))

result = execute_mcp_function(
    "find_best_distribution",
    {
        "demand": normal_demand
    },
    user_id=1
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Best Distribution: {result['best_distribution']}")
    print(f"Parameters: {result['parameters']}")
    print(f"Visualization ID: {result['visualization_id']}")
    print(f"Message: {result['message']}")
    print(f"Input Data - Mean: {result['input_data']['mean']:.2f}, Std: {result['input_data']['std']:.2f}")
else:
    print(f"Error: {result['message']}")

# Test 2: find_best_distribution (偏った分布)
print("\n" + "=" * 60)
print("Test 2: find_best_distribution (対数正規分布)")
print("=" * 60)
# 対数正規分布に従うデータ
lognormal_demand = list(np.random.lognormal(2, 0.5, 100))

result = execute_mcp_function(
    "find_best_distribution",
    {
        "demand": lognormal_demand
    },
    user_id=1
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Best Distribution: {result['best_distribution']}")
    print(f"Visualization ID: {result['visualization_id']}")
else:
    print(f"Error: {result['message']}")

# Test 3: visualize_demand_histogram
print("\n" + "=" * 60)
print("Test 3: visualize_demand_histogram")
print("=" * 60)
result = execute_mcp_function(
    "visualize_demand_histogram",
    {
        "demand": [10, 12, 8, 15, 11, 9, 13, 10, 14, 11, 12, 9, 10, 13, 11],
        "nbins": 10
    },
    user_id=1
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Visualization Type: {result['visualization_type']}")
    print(f"Statistics:")
    for key, value in result['statistics'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    print(f"Visualization ID: {result['visualization_id']}")
else:
    print(f"Error: {result['message']}")

# Test 4: compare_inventory_costs_visual
print("\n" + "=" * 60)
print("Test 4: compare_inventory_costs_visual")
print("=" * 60)
result = execute_mcp_function(
    "compare_inventory_costs_visual",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "holding_cost": 1.0,
        "stockout_cost": 10.0,
        "fixed_cost": 50.0,
        "n_samples": 10,
        "n_periods": 100
    },
    user_id=1
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Visualization Type: {result['visualization_type']}")
    print(f"\nCosts:")
    for policy, cost in result['costs'].items():
        print(f"  {policy}: {cost:.2f}円/日")
    print(f"\nRecommendation:")
    print(f"  Best Policy: {result['recommendation']['best_policy']}")
    print(f"  Best Cost: {result['recommendation']['best_cost']:.2f}円/日")
    print(f"  Savings vs Worst: {result['recommendation']['savings_vs_worst']:.2f}円/日")
    print(f"\nVisualization ID: {result['visualization_id']}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("All Phase 4 tests completed!")
print("=" * 60)

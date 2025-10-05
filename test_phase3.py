"""
Phase 3の3つの新機能をテストするスクリプト
"""
from mcp_tools import execute_mcp_function
import json

# Test 1: compare_inventory_policies
print("=" * 60)
print("Test 1: compare_inventory_policies")
print("=" * 60)
result = execute_mcp_function(
    "compare_inventory_policies",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "holding_cost": 1.0,
        "stockout_cost": 10.0,
        "fixed_cost": 50.0,
        "n_samples": 10,
        "n_periods": 100
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"\nComparison Type: {result['comparison_type']}")
    print(f"\n方策比較:")
    for policy_name, policy_data in result['policies'].items():
        print(f"\n  {policy_name}:")
        print(f"    {policy_data['policy_description']}")
        for key, value in policy_data.items():
            if key != 'policy_description':
                print(f"    {key}: {value}")

    print(f"\n推奨:")
    rec = result['recommendation']
    print(f"  最適方策: {rec['best_policy']}")
    print(f"  最小コスト: {rec['best_cost']:.2f}円/日")
    print(f"  理由: {rec['reasoning']}")
else:
    print(f"Error: {result['message']}")

# Test 2: calculate_safety_stock
print("\n" + "=" * 60)
print("Test 2: calculate_safety_stock (サービスレベル95%)")
print("=" * 60)
result = execute_mcp_function(
    "calculate_safety_stock",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "service_level": 0.95,
        "holding_cost": 1.0
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Calculation Type: {result['calculation_type']}")
    print(f"\n計算結果:")
    for key, value in result['results'].items():
        print(f"  {key}: {value:.2f}")
    print(f"\nサービスレベル:")
    print(f"  目標: {result['service_level']['percentage']}")
    print(f"  意味: {result['service_level']['meaning']}")
    if 'cost_analysis' in result:
        print(f"\nコスト分析:")
        print(f"  年間保管費用: {result['cost_analysis']['annual_holding_cost']:.2f}円")
else:
    print(f"Error: {result['message']}")

# Test 3: calculate_safety_stock (サービスレベル99%)
print("\n" + "=" * 60)
print("Test 3: calculate_safety_stock (サービスレベル99%)")
print("=" * 60)
result = execute_mcp_function(
    "calculate_safety_stock",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "service_level": 0.99
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"安全在庫: {result['results']['safety_stock']:.2f} units")
    print(f"発注点: {result['results']['reorder_point']:.2f} units")
    print(f"z値: {result['results']['z_value']:.2f}")
else:
    print(f"Error: {result['message']}")

# Test 4: visualize_inventory_simulation (QR方策)
print("\n" + "=" * 60)
print("Test 4: visualize_inventory_simulation (QR方策)")
print("=" * 60)
result = execute_mcp_function(
    "visualize_inventory_simulation",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "policy_type": "QR",
        "Q": 34.0,
        "R": 31.0,
        "holding_cost": 1.0,
        "stockout_cost": 10.0,
        "fixed_cost": 50.0,
        "n_periods": 100
    },
    user_id=1
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Visualization Type: {result['visualization_type']}")
    print(f"Visualization ID: {result['visualization_id']}")
    print(f"\nPolicy Info:")
    print(f"  Type: {result['policy_info']['policy_type']}")
    print(f"  Parameters: {result['policy_info']['parameters']}")
    print(f"\nSimulation Stats:")
    for key, value in result['simulation_stats'].items():
        print(f"  {key}: {value}")
    print(f"\n{result['message']}")
else:
    print(f"Error: {result['message']}")

# Test 5: visualize_inventory_simulation (sS方策)
print("\n" + "=" * 60)
print("Test 5: visualize_inventory_simulation (sS方策)")
print("=" * 60)
result = execute_mcp_function(
    "visualize_inventory_simulation",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "policy_type": "sS",
        "s": 28.0,
        "S": 54.0,
        "holding_cost": 1.0,
        "stockout_cost": 10.0,
        "fixed_cost": 50.0,
        "n_periods": 100
    },
    user_id=1
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Visualization ID: {result['visualization_id']}")
    print(f"Average Inventory: {result['simulation_stats']['average_inventory']:.2f}")
    print(f"Stockouts: {result['simulation_stats']['stockouts']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("All Phase 3 tests completed!")
print("=" * 60)

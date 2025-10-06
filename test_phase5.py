"""
Phase 5: 多段階在庫シミュレーション機能のテスト
"""

from mcp_tools import execute_mcp_function
import numpy as np

print("=" * 60)
print("Test 1: simulate_multistage_inventory (3段階)")
print("=" * 60)

result = execute_mcp_function(
    "simulate_multistage_inventory",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_times": [2, 3, 1],
        "holding_costs": [1.0, 2.0, 5.0],
        "stockout_cost": 100.0,
        "fixed_cost": 50.0,
        "n_samples": 10,
        "n_periods": 100
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Simulation Type: {result['simulation_type']}")
    print(f"Number of Stages: {result['parameters']['n_stages']}")
    print(f"Average Cost: {result['simulation_results']['average_cost_per_period']:.2f} ± {result['simulation_results']['cost_std_dev']:.2f}")
    print(f"Stage Details:")
    for stage in result['stage_details']:
        print(f"  Stage {stage['stage']}: LT={stage['lead_time']}, h={stage['holding_cost']}, Avg Inv={stage['avg_inventory']:.2f}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 2: simulate_base_stock_policy")
print("=" * 60)

# 需要データ生成
np.random.seed(42)
demand_data = list(np.random.normal(10, 2, 50))

result = execute_mcp_function(
    "simulate_base_stock_policy",
    {
        "demand": demand_data,
        "base_stock_level": 50.0,
        "lead_time": 3,
        "capacity": 1000,
        "holding_cost": 1.0,
        "stockout_cost": 100.0,
        "n_samples": 5
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Policy Type: {result['policy_type']}")
    print(f"Base Stock Level: {result['parameters']['base_stock_level_S']}")
    print(f"Total Cost: {result['simulation_results']['total_cost_per_period']:.2f}")
    print(f"Derivative dC/dS: {result['simulation_results']['derivative_dC_dS']:.4f}")
    print(f"Inventory Statistics:")
    print(f"  Average Inventory: {result['inventory_statistics']['average_inventory']:.2f}")
    print(f"  Stockout Rate: {result['inventory_statistics']['stockout_rate']*100:.1f}%")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 3: calculate_base_stock_levels")
print("=" * 60)

result = execute_mcp_function(
    "calculate_base_stock_levels",
    {
        "nodes": [
            {"name": "retailer", "lead_time": 1},
            {"name": "warehouse", "lead_time": 3},
            {"name": "supplier", "lead_time": 5}
        ],
        "mu": 10.0,
        "sigma": 2.0,
        "service_level": 0.95
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Calculation Type: {result['calculation_type']}")
    print(f"Service Level: {result['parameters']['service_level']*100:.0f}%")
    print(f"Z-value: {result['parameters']['z_value']:.3f}")
    print(f"Node Results:")
    for node in result['node_results']:
        print(f"  {node['node_name']}:")
        print(f"    Lead Time: {node['lead_time']}, Echelon LT: {node['echelon_lead_time']}")
        print(f"    Base Stock: {node['base_stock_level']:.2f}, Safety Stock: {node['safety_stock']:.2f}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("Test 4: simulate_multistage_inventory (2段階)")
print("=" * 60)

result = execute_mcp_function(
    "simulate_multistage_inventory",
    {
        "mu": 15.0,
        "sigma": 3.0,
        "lead_times": [2, 4],
        "holding_costs": [2.0, 1.0],
        "stockout_cost": 150.0,
        "fixed_cost": 100.0,
        "n_samples": 20,
        "n_periods": 200
    },
    user_id=1
)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Number of Stages: {result['parameters']['n_stages']}")
    print(f"Average Cost: {result['simulation_results']['average_cost_per_period']:.2f}")
    print(f"Message: {result['message']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("All Phase 5 tests completed!")
print("=" * 60)

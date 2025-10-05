"""
Phase 1の4つの新機能をテストするスクリプト
"""
from mcp_tools import execute_mcp_function

# Test 1: simulate_qr_policy
print("=" * 60)
print("Test 1: simulate_qr_policy")
print("=" * 60)
result = execute_mcp_function(
    "simulate_qr_policy",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "Q": 50.0,
        "R": 35.0,
        "holding_cost": 1.0,
        "stockout_cost": 10.0,
        "fixed_cost": 50.0,
        "n_samples": 10,
        "n_periods": 100
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Policy Type: {result['policy_type']}")
    print(f"Average Cost: {result['simulation_results']['average_cost_per_period']:.2f}")
    print(f"Q={result['parameters']['order_quantity_Q']}, R={result['parameters']['reorder_point_R']}")
else:
    print(f"Error: {result['message']}")

# Test 2: optimize_qr_policy
print("\n" + "=" * 60)
print("Test 2: optimize_qr_policy")
print("=" * 60)
result = execute_mcp_function(
    "optimize_qr_policy",
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
    print(f"Policy Type: {result['policy_type']}")
    print(f"Optimal Q: {result['optimal_parameters']['optimal_order_quantity_Q']:.2f}")
    print(f"Optimal R: {result['optimal_parameters']['optimal_reorder_point_R']:.2f}")
    print(f"Minimum Cost: {result['optimization_results']['minimum_average_cost']:.2f}")
else:
    print(f"Error: {result['message']}")

# Test 3: simulate_ss_policy
print("\n" + "=" * 60)
print("Test 3: simulate_ss_policy")
print("=" * 60)
result = execute_mcp_function(
    "simulate_ss_policy",
    {
        "mu": 10.0,
        "sigma": 2.0,
        "lead_time": 3,
        "s": 30.0,
        "S": 60.0,
        "holding_cost": 1.0,
        "stockout_cost": 10.0,
        "fixed_cost": 50.0,
        "n_samples": 10,
        "n_periods": 100
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Policy Type: {result['policy_type']}")
    print(f"Average Cost: {result['simulation_results']['average_cost_per_period']:.2f}")
    print(f"s={result['parameters']['reorder_point_s']}, S={result['parameters']['base_stock_level_S']}")
else:
    print(f"Error: {result['message']}")

# Test 4: optimize_ss_policy
print("\n" + "=" * 60)
print("Test 4: optimize_ss_policy")
print("=" * 60)
result = execute_mcp_function(
    "optimize_ss_policy",
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
    print(f"Policy Type: {result['policy_type']}")
    print(f"Optimal s: {result['optimal_parameters']['optimal_reorder_point_s']:.2f}")
    print(f"Optimal S: {result['optimal_parameters']['optimal_base_stock_level_S']:.2f}")
    print(f"Minimum Cost: {result['optimization_results']['minimum_average_cost']:.2f}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("All Phase 1 tests completed!")
print("=" * 60)

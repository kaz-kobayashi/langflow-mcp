"""
Phase 2の2つの新機能をテストするスクリプト
"""
from mcp_tools import execute_mcp_function

# Test 1: calculate_wagner_whitin
print("=" * 60)
print("Test 1: calculate_wagner_whitin")
print("=" * 60)
result = execute_mcp_function(
    "calculate_wagner_whitin",
    {
        "demand": [10, 20, 30, 15],
        "fixed_cost": 100.0,
        "holding_cost": 5.0,
        "variable_cost": 0.0
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Algorithm: {result['algorithm']}")
    print(f"Total Cost: {result['results']['total_cost']:.2f}円")
    print(f"Order Schedule: {result['results']['order_schedule']}")
    print(f"Order Periods: {result['results']['order_periods']}")
    print(f"Number of Orders: {result['results']['number_of_orders']}")
    print(f"Summary: {result['summary']}")
else:
    print(f"Error: {result['message']}")

# Test 2: analyze_demand_pattern (安定需要)
print("\n" + "=" * 60)
print("Test 2: analyze_demand_pattern (安定需要)")
print("=" * 60)
result = execute_mcp_function(
    "analyze_demand_pattern",
    {
        "demand": [10, 11, 9, 10, 12, 10, 11, 9, 10, 11]
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Analysis Type: {result['analysis_type']}")
    stats = result['statistics']
    print(f"Mean: {stats['mean']:.2f}")
    print(f"Std Dev: {stats['standard_deviation']:.2f}")
    print(f"CV: {stats['coefficient_of_variation']:.3f}")
    print(f"Min: {stats['min']}, Max: {stats['max']}")
    print(f"Pattern Type: {result['pattern_assessment']['pattern_type']}")
    print(f"Recommendation: {result['pattern_assessment']['recommendation']}")
else:
    print(f"Error: {result['message']}")

# Test 3: analyze_demand_pattern (変動需要)
print("\n" + "=" * 60)
print("Test 3: analyze_demand_pattern (変動需要)")
print("=" * 60)
result = execute_mcp_function(
    "analyze_demand_pattern",
    {
        "demand": [5, 20, 8, 30, 12, 25, 7, 18, 10, 22]
    }
)
print(f"Status: {result['status']}")
if result['status'] == 'success':
    stats = result['statistics']
    print(f"Mean: {stats['mean']:.2f}")
    print(f"Std Dev: {stats['standard_deviation']:.2f}")
    print(f"CV: {stats['coefficient_of_variation']:.3f}")
    print(f"Pattern Type: {result['pattern_assessment']['pattern_type']}")
    print(f"Recommendation: {result['pattern_assessment']['recommendation']}")
else:
    print(f"Error: {result['message']}")

print("\n" + "=" * 60)
print("All Phase 2 tests completed!")
print("=" * 60)

"""
Test the compare_inventory_policies MCP function
"""
import sys
sys.path.append('.')

from mcp_tools import execute_mcp_function

# Test parameters from example 9.1
arguments = {
    "mu": 100,
    "sigma": 15,
    "lead_time": 5,
    "holding_cost": 1,
    "stockout_cost": 100,
    "fixed_cost": 500,
    "n_samples": 50,
    "n_periods": 200
}

print("=" * 60)
print("Testing compare_inventory_policies MCP function")
print("=" * 60)
print()

result = execute_mcp_function("compare_inventory_policies", arguments, user_id="test_user")

if result["status"] == "success":
    print("✓ Function executed successfully")
    print()

    print("Policy Results:")
    print("-" * 60)

    # EOQ
    eoq = result["policies"]["EOQ"]
    print(f"EOQ方策:")
    print(f"  最適発注量 Q: {eoq['optimal_Q']:.2f}")
    print(f"  日次総コスト: {eoq['daily_cost']:.2f}円/日")
    print()

    # (Q,R)
    qr = result["policies"]["QR_policy"]
    print(f"(Q,R)方策:")
    print(f"  最適発注量 Q: {qr['optimal_Q']}")
    print(f"  最適発注点 R: {qr['optimal_R']}")
    print(f"  平均コスト: {qr['average_cost']:.2f}円/日")
    print()

    # (s,S)
    ss = result["policies"]["sS_policy"]
    print(f"(s,S)方策:")
    print(f"  最適発注点 s: {ss['optimal_s']}")
    print(f"  最適目標在庫 S: {ss['optimal_S']}")
    print(f"  平均コスト: {ss['average_cost']:.2f}円/日")
    print()

    print("Recommendation:")
    print("-" * 60)
    rec = result["recommendation"]
    print(f"最適方策: {rec['best_policy']}")
    print(f"最適コスト: {rec['best_cost']:.2f}円/日")
    print()
    print("Cost Comparison (daily):")
    for policy, cost in rec["cost_comparison"].items():
        print(f"  {policy}: {cost:.2f}円/日")
    print()

    # Verify costs are reasonable
    eoq_daily = eoq['daily_cost']
    qr_cost = qr['average_cost']
    ss_cost = ss['average_cost']

    print("Verification:")
    print("-" * 60)
    if qr_cost > eoq_daily * 10:
        print(f"✗ ERROR: (Q,R) cost ({qr_cost:.2f}) is {qr_cost/eoq_daily:.1f}x higher than EOQ ({eoq_daily:.2f})")
    else:
        print(f"✓ (Q,R) cost ({qr_cost:.2f}) is reasonable ({qr_cost/eoq_daily:.1f}x EOQ)")

    if ss_cost > eoq_daily * 10:
        print(f"✗ ERROR: (s,S) cost ({ss_cost:.2f}) is {ss_cost/eoq_daily:.1f}x higher than EOQ ({eoq_daily:.2f})")
    else:
        print(f"✓ (s,S) cost ({ss_cost:.2f}) is reasonable ({ss_cost/eoq_daily:.1f}x EOQ)")

else:
    print(f"✗ Error: {result.get('message', 'Unknown error')}")

"""Test script for SCRM optimization tools"""

import sys
sys.path.append('.')

from scmopt2.scrm import prepare, optimize_scrm_expected, optimize_scrm_cvar, compare_scrm_policies

def test_optimization():
    print("=== Testing SCRM Optimization Tools ===\n")

    # データを読み込み
    print("1. Loading test data...")
    filename_suffix = "test_01"
    folder = "./data/scrm/"

    try:
        Demand, UB, Capacity, Pipeline, R, BOM, Product, G, ProdGraph, pos, pos2, pos3, \
            _, _, _, _ = prepare(filename_suffix, folder)
        print(f"   ✓ Data loaded successfully")
        print(f"   - Plants: {list(Capacity.keys())}")
        print(f"   - Products in ProdGraph: {len(ProdGraph.nodes())}")
        print(f"   - Demand nodes: {len(Demand)}")
    except Exception as e:
        print(f"   ✗ Error loading data: {e}")
        return False

    # テスト用のコストパラメータを設定
    print("\n2. Setting up cost parameters...")
    h_cost = {}  # 在庫保管費用
    b_cost = {}  # 品切れ費用

    for (plant, prod) in ProdGraph.nodes():
        h_cost[(plant, prod)] = 1.0  # 在庫保管費用 = 1.0
        b_cost[(plant, prod)] = 10.0  # 品切れ費用 = 10.0

    # 途絶確率とTTRを設定
    disruption_prob = {}
    TTR = {}
    for plant in Capacity.keys():
        disruption_prob[plant] = 0.1  # 各工場10%の途絶確率
        TTR[plant] = 2  # 回復時間2期

    print(f"   ✓ Cost parameters set")
    print(f"   - Holding cost: {h_cost[list(h_cost.keys())[0]]}")
    print(f"   - Backorder cost: {b_cost[list(b_cost.keys())[0]]}")
    print(f"   - Disruption probability: {disruption_prob[0]}")
    print(f"   - Time to recover: {TTR[0]}")

    # 期待値最小化を実行
    print("\n3. Testing Expected Value Optimization...")
    try:
        expected_result = optimize_scrm_expected(
            Demand, UB, Capacity, Pipeline, R, Product, ProdGraph, BOM, G,
            h_cost, b_cost, disruption_prob, TTR, K_max=2
        )
        print(f"   ✓ Expected value optimization completed")
        print(f"   - Total cost: {expected_result['total_cost']:.2f}")
        print(f"   - Inventory cost: {expected_result['expected_inventory_cost']:.2f}")
        print(f"   - Backorder cost: {expected_result['expected_backorder_cost']:.2f}")
        print(f"   - Number of scenarios: {expected_result['num_scenarios']}")
    except Exception as e:
        print(f"   ✗ Error in expected value optimization: {e}")
        import traceback
        traceback.print_exc()
        return False

    # CVaR最小化を実行
    print("\n4. Testing CVaR Optimization...")
    try:
        cvar_result = optimize_scrm_cvar(
            Demand, UB, Capacity, Pipeline, R, Product, ProdGraph, BOM, G,
            h_cost, b_cost, disruption_prob, TTR, beta=0.95, K_max=2
        )
        print(f"   ✓ CVaR optimization completed")
        print(f"   - CVaR: {cvar_result['cvar']:.2f}")
        print(f"   - VaR: {cvar_result['var']:.2f}")
        print(f"   - Expected cost: {cvar_result['expected_cost']:.2f}")
        print(f"   - Beta: {cvar_result['beta']}")
    except Exception as e:
        print(f"   ✗ Error in CVaR optimization: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 方針比較を実行
    print("\n5. Testing Policy Comparison...")
    try:
        comparison_result = compare_scrm_policies(
            Demand, UB, Capacity, Pipeline, R, Product, ProdGraph, BOM, G,
            h_cost, b_cost, disruption_prob, TTR, beta=0.95, K_max=2
        )
        print(f"   ✓ Policy comparison completed")
        print(f"   - Expected policy cost: {comparison_result['comparison']['expected_total_cost']:.2f}")
        print(f"   - CVaR policy cost: {comparison_result['comparison']['cvar_total_cost']:.2f}")
        print(f"   - Cost increase: {comparison_result['comparison']['cost_increase_pct']:.2f}%")
        print(f"   - Recommendation: {comparison_result['recommendation']}")
    except Exception as e:
        print(f"   ✗ Error in policy comparison: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n=== All Tests Passed! ===")
    return True

if __name__ == "__main__":
    success = test_optimization()
    sys.exit(0 if success else 1)

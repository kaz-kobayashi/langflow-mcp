"""Test script for Phase 3 LND visualization tool"""

import sys
import pandas as pd
sys.path.append('.')

from mcp_tools import execute_mcp_function

# サンプルデータディレクトリ
DATA_DIR = "nbs/data/"


def test_visualize_lnd_result():
    """Test 1: LND最適化結果の可視化（最適化後）"""
    print("=== Test 1: visualize_lnd_result ===\n")

    try:
        # Step 1: まずLND最適化を実行
        print("   Step 1: Running LND optimization...")

        # データ読み込み
        prod_df = pd.read_csv(DATA_DIR + "prod.csv")
        cust_df = pd.read_csv(DATA_DIR + "cust.csv").head(5)
        dc_df = pd.read_csv(DATA_DIR + "DC.csv").head(3)
        plnt_df = pd.read_csv(DATA_DIR + "Plnt.csv")
        plnt_prod_df = pd.read_csv(DATA_DIR + "Plnt-Prod.csv")
        total_demand_df = pd.read_csv(DATA_DIR + "total_demand.csv").head(10)
        trans_df = pd.read_csv(DATA_DIR + "trans_cost.csv").head(50)

        optimize_arguments = {
            "prod_data": prod_df.to_dict(orient="records"),
            "cust_data": cust_df.to_dict(orient="records"),
            "dc_data": dc_df.to_dict(orient="records"),
            "plnt_data": plnt_df.to_dict(orient="records"),
            "plnt_prod_data": plnt_prod_df.to_dict(orient="records"),
            "total_demand_data": total_demand_df.to_dict(orient="records"),
            "trans_data": trans_df.to_dict(orient="records"),
            "dc_num": [1, 2],
            "single_sourcing": True,
            "max_cpu": 30
        }

        optimize_result = execute_mcp_function("solve_lnd", optimize_arguments, user_id=2001)
        print(f"   Optimization Status: {optimize_result.get('status')}")

        if optimize_result.get('status') != 'success':
            print(f"   ✗ Optimization failed: {optimize_result.get('message')}")
            return False

        print(f"   ✓ Optimization completed (Total Cost: {optimize_result.get('total_cost', 0):.2f})")

        # Step 2: 可視化を実行
        print("   Step 2: Visualizing optimization result...")
        viz_result = execute_mcp_function("visualize_lnd_result", {}, user_id=2001)
        print(f"   Visualization Status: {viz_result.get('status')}")

        if viz_result.get('status') == 'success':
            print(f"   ✓ Visualization created")
            print(f"   ✓ Visualization URL: {viz_result.get('visualization_url')}")
            print(f"   ✓ Visualization ID: {viz_result.get('visualization_id')}")
            print(f"   ✓ Customers: {viz_result.get('num_customers')}")
            print(f"   ✓ DCs: {viz_result.get('num_dcs')}")
            print(f"   ✓ Plants: {viz_result.get('num_plants')}")
            print(f"   ✓ Flows: {viz_result.get('num_flows')}")
            return True
        else:
            print(f"   ✗ Visualization failed: {viz_result.get('message')}")
            if 'traceback' in viz_result:
                print(f"   Traceback: {viz_result['traceback'][:500]}")
            return False

    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visualize_without_optimization():
    """Test 2: 最適化なしで可視化（エラー確認）"""
    print("\n=== Test 2: visualize_lnd_result without prior optimization (expected to fail) ===\n")

    try:
        viz_result = execute_mcp_function("visualize_lnd_result", {}, user_id=2002)
        print(f"   Status: {viz_result.get('status')}")

        if viz_result.get('status') == 'error':
            print(f"   ✓ Correctly failed with message: {viz_result.get('message')}")
            return True
        else:
            print(f"   ✗ Should have failed but got status: {viz_result.get('status')}")
            return False

    except Exception as e:
        print(f"   ✗ Unexpected exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 3: LND Visualization Tool Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("visualize_lnd_result", test_visualize_lnd_result()))
    results.append(("visualize_without_optimization (error handling)", test_visualize_without_optimization()))

    # Summary
    print("\n" + "=" * 60)
    print("  Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All Phase 3 LND tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

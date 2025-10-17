"""Test script for Phase 3 lotsizing visualization tools"""

import sys
sys.path.append('.')

from mcp_tools import execute_mcp_function

def test_visualize_lotsizing_basic():
    """Test 1: Visualize basic lotsizing optimization result"""
    print("=== Test 1: Visualize Basic Lotsizing Result ===\n")

    # Step 1: まず基本ロットサイズ最適化を実行
    print("   Step 1: Running basic lotsizing optimization...")
    optimize_arguments = {
        "item_data": [
            {"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100}
        ],
        "production_data": [
            {"name": "Product1", "SetupTime": 30, "SetupCost": 500, "ProdTime": 2, "ProdCost": 10}
        ],
        "demand": [[100, 120, 110, 130, 140, 125, 135, 145, 150, 160]],
        "resource_data": [
            {"name": "Res1", "period": t, "capacity": 2000} for t in range(10)
        ],
        "max_cpu": 60,
        "solver": "CBC",
        "visualize": False
    }

    try:
        optimize_result = execute_mcp_function("optimize_lotsizing", optimize_arguments, user_id=999)
        print(f"   Optimization Status: {optimize_result.get('status')}")
        if optimize_result.get('status') != 'success':
            print(f"   ✗ Optimization failed: {optimize_result.get('message')}")
            return False
        print(f"   ✓ Optimization completed (Objective: {optimize_result.get('objective_value', 0):.2f})")

        # Step 2: 可視化ツールを実行
        print("   Step 2: Visualizing optimization result...")
        viz_result = execute_mcp_function("visualize_lotsizing_result", {}, user_id=999)
        print(f"   Visualization Status: {viz_result.get('status')}")

        if viz_result.get('status') == 'success':
            print(f"   ✓ Visualization created")
            print(f"   ✓ Inventory viz URL: {viz_result.get('inventory_visualization_url')}")
            print(f"   ✓ Production viz URL: {viz_result.get('production_visualization_url')}")
            print(f"   ✓ Message: {viz_result.get('message')}")
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


def test_visualize_multimode_lotsizing():
    """Test 2: Visualize multimode lotsizing optimization result"""
    print("\n=== Test 2: Visualize Multimode Lotsizing Result ===\n")

    # Step 1: まずマルチモードロットサイズ最適化を実行
    print("   Step 1: Running multimode lotsizing optimization...")

    T = 5
    optimize_arguments = {
        "item_data": [
            {"name": "Product1", "inv_cost": 1.0, "safety_inventory": 50, "target_inventory": 1000,
             "initial_inventory": 100, "final_inventory": 50}
        ],
        "resource_data": [
            {"name": "Machine1", "capacity": 8000}
        ],
        "process_data": [
            {"item": "Product1", "mode": "Fast", "setup_cost": 500, "prod_cost": 15, "n_resources": 1},
            {"item": "Product1", "mode": "Slow", "setup_cost": 300, "prod_cost": 12, "n_resources": 1}
        ],
        "bom_data": [],
        "usage_data": [
            {"item": "Product1", "mode": "Fast", "resource": "Machine1", "setup_time": 60, "prod_time": 5},
            {"item": "Product1", "mode": "Slow", "resource": "Machine1", "setup_time": 30, "prod_time": 8}
        ],
        "demand": {f"{t},Product1": [100, 120, 110, 130, 140][t] for t in range(T)},
        "capacity": {f"{t},Machine1": 8000 for t in range(T)},
        "T": T,
        "visualize": False
    }

    try:
        optimize_result = execute_mcp_function("optimize_multimode_lotsizing", optimize_arguments, user_id=998)
        print(f"   Optimization Status: {optimize_result.get('status')}")
        if optimize_result.get('status') != 'success':
            print(f"   ✗ Optimization failed: {optimize_result.get('message')}")
            return False
        print(f"   ✓ Optimization completed (Objective: {optimize_result.get('objective_value', 0):.2f})")

        # Step 2: 可視化ツールを実行
        print("   Step 2: Visualizing optimization result...")
        viz_result = execute_mcp_function("visualize_multimode_lotsizing_result", {}, user_id=998)
        print(f"   Visualization Status: {viz_result.get('status')}")

        if viz_result.get('status') == 'success':
            print(f"   ✓ Visualization created")
            print(f"   ✓ Inventory viz URL: {viz_result.get('inventory_visualization_url')}")
            print(f"   ✓ Production viz URL: {viz_result.get('production_visualization_url')}")
            print(f"   ✓ Message: {viz_result.get('message')}")
            print(f"   ✓ Periods: {viz_result.get('periods')}")
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
    """Test 3: Try to visualize without running optimization first (should fail gracefully)"""
    print("\n=== Test 3: Visualize Without Prior Optimization (Expected to Fail) ===\n")

    try:
        viz_result = execute_mcp_function("visualize_lotsizing_result", {}, user_id=997)
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
    print("  Phase 3: Lotsizing Visualization Tools Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Visualize basic lotsizing result", test_visualize_lotsizing_basic()))
    results.append(("Visualize multimode lotsizing result", test_visualize_multimode_lotsizing()))
    results.append(("Visualize without optimization (error handling)", test_visualize_without_optimization()))

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
        print("\n🎉 All Phase 3 tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

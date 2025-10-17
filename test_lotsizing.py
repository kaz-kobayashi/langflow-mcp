"""Test script for lotsizing optimization tools"""

import sys
sys.path.append('.')

from mcp_tools import execute_mcp_function

def test_basic_lotsizing_no_bom():
    """Test 1: Basic lotsizing without BOM"""
    print("=== Test 1: Basic Lotsizing (No BOM) ===\n")

    arguments = {
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
        result = execute_mcp_function("optimize_lotsizing", arguments)
        print(f"   Status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"   ✓ Objective value: {result.get('objective_value', 'N/A'):.2f}")
            print(f"   ✓ Periods: {result.get('periods', 'N/A')}")
            print(f"   ✓ Solver: {result.get('solver', 'N/A')}")
            print(f"   ✓ Message: {result.get('message', 'N/A')}")
            return True
        else:
            print(f"   ✗ Error: {result.get('message')}")
            if 'traceback' in result:
                print(f"   Traceback: {result['traceback'][:500]}")
            return False
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_lotsizing_with_bom():
    """Test 2: Basic lotsizing with BOM"""
    print("\n=== Test 2: Basic Lotsizing (With BOM) ===\n")

    arguments = {
        "item_data": [
            {"name": "Material1", "inv_cost": 0.5, "safety_inventory": 0, "target_inventory": 2000, "initial_inventory": 200},
            {"name": "Product1", "inv_cost": 2.0, "safety_inventory": 50, "target_inventory": 1000, "initial_inventory": 100}
        ],
        "production_data": [
            {"name": "Material1", "SetupTime": 20, "SetupCost": 300, "ProdTime": 1, "ProdCost": 5},
            {"name": "Product1", "SetupTime": 30, "SetupCost": 500, "ProdTime": 2, "ProdCost": 10}
        ],
        "bom_data": [
            {"child": "Material1", "parent": "Product1", "units": 2.0}
        ],
        "demand": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Material1 (no external demand)
                  [100, 120, 110, 130, 140, 125, 135, 145, 150, 160]],  # Product1
        "resource_data": [
            {"name": "Res0", "period": t, "capacity": 2000} for t in range(10)
        ] + [
            {"name": "Res1", "period": t, "capacity": 2000} for t in range(10)
        ],
        "max_cpu": 60,
        "solver": "CBC",
        "visualize": False
    }

    try:
        result = execute_mcp_function("optimize_lotsizing", arguments)
        print(f"   Status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"   ✓ Objective value: {result.get('objective_value', 'N/A'):.2f}")
            print(f"   ✓ Periods: {result.get('periods', 'N/A')}")
            return True
        else:
            print(f"   ✗ Error: {result.get('message')}")
            if 'traceback' in result:
                print(f"   Traceback: {result['traceback'][:500]}")
            return False
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multimode_lotsizing_single_product():
    """Test 3: Multimode lotsizing with single product"""
    print("\n=== Test 3: Multimode Lotsizing (Single Product, 2 Modes) ===\n")

    T = 5
    arguments = {
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
        "bom_data": [],  # No BOM for this test
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
        result = execute_mcp_function("optimize_multimode_lotsizing", arguments)
        print(f"   Status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"   ✓ Objective value: {result.get('objective_value', 'N/A'):.2f}")
            costs = result.get('costs', {})
            print(f"   ✓ Costs breakdown:")
            print(f"      - Demand violation penalty: {costs.get('demand_violation_penalty', 0):.2f}")
            print(f"      - Inventory violation penalty: {costs.get('inventory_violation_penalty', 0):.2f}")
            print(f"      - Setup cost: {costs.get('setup_cost', 0):.2f}")
            print(f"      - Production cost: {costs.get('production_cost', 0):.2f}")
            print(f"      - Inventory cost: {costs.get('inventory_cost', 0):.2f}")
            print(f"   ✓ Periods: {result.get('periods', 'N/A')}")
            return True
        else:
            print(f"   ✗ Error: {result.get('message')}")
            if 'traceback' in result:
                print(f"   Traceback: {result['traceback'][:500]}")
            return False
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multimode_lotsizing_multiple_products():
    """Test 4: Multimode lotsizing with multiple products and BOM"""
    print("\n=== Test 4: Multimode Lotsizing (2 Products with BOM) ===\n")

    T = 5
    arguments = {
        "item_data": [
            {"name": "Material1", "inv_cost": 0.5, "safety_inventory": 0, "target_inventory": 2000,
             "initial_inventory": 200, "final_inventory": 100},
            {"name": "Product1", "inv_cost": 2.0, "safety_inventory": 50, "target_inventory": 1000,
             "initial_inventory": 100, "final_inventory": 50}
        ],
        "resource_data": [
            {"name": "Machine1", "capacity": 8000},
            {"name": "Machine2", "capacity": 6000}
        ],
        "process_data": [
            {"item": "Material1", "mode": "Standard", "setup_cost": 300, "prod_cost": 5, "n_resources": 1},
            {"item": "Product1", "mode": "Fast", "setup_cost": 500, "prod_cost": 15, "n_resources": 1},
            {"item": "Product1", "mode": "Slow", "setup_cost": 300, "prod_cost": 12, "n_resources": 1}
        ],
        "bom_data": [
            {"item": "Product1", "mode": "Fast", "child": "Material1", "units": 1.5},
            {"item": "Product1", "mode": "Slow", "child": "Material1", "units": 2.0}
        ],
        "usage_data": [
            {"item": "Material1", "mode": "Standard", "resource": "Machine1", "setup_time": 30, "prod_time": 3},
            {"item": "Product1", "mode": "Fast", "resource": "Machine2", "setup_time": 60, "prod_time": 5},
            {"item": "Product1", "mode": "Slow", "resource": "Machine2", "setup_time": 30, "prod_time": 8}
        ],
        "demand": {
            **{f"{t},Material1": 0 for t in range(T)},  # No external demand for material
            **{f"{t},Product1": [100, 120, 110, 130, 140][t] for t in range(T)}
        },
        "capacity": {
            **{f"{t},Machine1": 8000 for t in range(T)},
            **{f"{t},Machine2": 6000 for t in range(T)}
        },
        "T": T,
        "visualize": False
    }

    try:
        result = execute_mcp_function("optimize_multimode_lotsizing", arguments)
        print(f"   Status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"   ✓ Objective value: {result.get('objective_value', 'N/A'):.2f}")
            costs = result.get('costs', {})
            print(f"   ✓ Costs breakdown:")
            print(f"      - Setup cost: {costs.get('setup_cost', 0):.2f}")
            print(f"      - Production cost: {costs.get('production_cost', 0):.2f}")
            print(f"      - Inventory cost: {costs.get('inventory_cost', 0):.2f}")
            return True
        else:
            print(f"   ✗ Error: {result.get('message')}")
            if 'traceback' in result:
                print(f"   Traceback: {result['traceback'][:500]}")
            return False
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("  Lotsizing Optimization Tools Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Basic lotsizing (no BOM)", test_basic_lotsizing_no_bom()))
    results.append(("Basic lotsizing (with BOM)", test_basic_lotsizing_with_bom()))
    results.append(("Multimode lotsizing (single product)", test_multimode_lotsizing_single_product()))
    results.append(("Multimode lotsizing (multiple products)", test_multimode_lotsizing_multiple_products()))

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
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)

"""
Comprehensive test script for all non-visualization MCP functions
テスト結果を test_results.md に出力
"""
import sys
sys.path.append('.')

from mcp_tools import execute_mcp_function
import json
from datetime import datetime

# テスト結果を格納
test_results = []

def test_function(category, tool_name, description, arguments, expected_status="success"):
    """MCPツールをテストして結果を記録"""
    print(f"\n{'='*60}")
    print(f"Testing: {tool_name}")
    print(f"Category: {category}")
    print(f"Description: {description}")
    print(f"{'='*60}")

    try:
        result = execute_mcp_function(tool_name, arguments, user_id="test_user")

        status = result.get("status", "unknown")
        success = status == expected_status

        test_result = {
            "category": category,
            "tool_name": tool_name,
            "description": description,
            "status": status,
            "success": success,
            "result_summary": {}
        }

        # 結果のサマリーを抽出
        if success:
            print(f"✓ Test PASSED")
            # 主要な結果を抽出
            for key in ["best_cost", "optimal_Q", "optimal_R", "optimal_s", "optimal_S",
                       "safety_stock", "reorder_point", "cost", "total_cost", "forecast"]:
                if key in result:
                    test_result["result_summary"][key] = result[key]
                    print(f"  {key}: {result[key]}")
        else:
            print(f"✗ Test FAILED")
            print(f"  Error: {result.get('message', 'Unknown error')}")
            test_result["error_message"] = result.get("message", "Unknown error")
            if "traceback" in result:
                test_result["traceback"] = result["traceback"][:500]  # 最初の500文字のみ

        test_results.append(test_result)
        return success

    except Exception as e:
        print(f"✗ Test EXCEPTION: {str(e)}")
        test_results.append({
            "category": category,
            "tool_name": tool_name,
            "description": description,
            "status": "exception",
            "success": False,
            "error_message": str(e)
        })
        return False


# ================================
# Category 1: 在庫最適化（4ツール）
# ================================

print("\n" + "="*60)
print("Category 1: 在庫最適化（4ツール）")
print("="*60)

# 1.1 optimize_safety_stock_allocation
test_function(
    category="在庫最適化",
    tool_name="optimize_safety_stock_allocation",
    description="タブーサーチによる安全在庫配置の最適化",
    arguments={
        "items_data": json.dumps([
            {"name": "原材料", "h": 1.0, "b": 50.0, "average_demand": 0, "std_demand": 0,
             "lead_time": 2.0, "echelon_lead_time": 5.0},
            {"name": "中間品", "h": 2.0, "b": 100.0, "average_demand": 0, "std_demand": 0,
             "lead_time": 2.0, "echelon_lead_time": 3.0},
            {"name": "最終製品", "h": 5.0, "b": 150.0, "average_demand": 100.0, "std_demand": 20.0,
             "lead_time": 1.0, "echelon_lead_time": 1.0}
        ]),
        "bom_data": json.dumps([
            {"child": "原材料", "parent": "中間品", "units": 1.0},
            {"child": "中間品", "parent": "最終製品", "units": 1.0}
        ]),
        "z": 1.65,
        "max_iter": 100,
        "tabu_tenure": 5
    }
)

# 1.2 calculate_safety_stock
test_function(
    category="在庫最適化",
    tool_name="calculate_safety_stock",
    description="安全在庫の計算",
    arguments={
        "average_demand": 100,
        "demand_std": 15,
        "lead_time": 7,
        "service_level": 0.95
    }
)

# 1.3 optimize_periodic_inventory
test_function(
    category="在庫最適化",
    tool_name="optimize_periodic_inventory",
    description="定期発注方策の最適化（Adam）",
    arguments={
        "network_data": json.dumps({
            "stages": [
                {"name": "原材料", "average_demand": 0, "sigma": 0, "h": 1.0, "b": 50,
                 "capacity": 1000, "net_replenishment_time": 2},
                {"name": "製品", "average_demand": 100, "sigma": 20, "h": 5.0, "b": 150,
                 "capacity": 500, "net_replenishment_time": 1}
            ],
            "connections": [
                {"child": "原材料", "parent": "製品", "units": 1, "allocation": 1.0}
            ]
        }),
        "max_iter": 50,
        "n_samples": 10,
        "n_periods": 50,
        "algorithm": "adam"
    }
)

# 1.4 optimize_ss_policy
test_function(
    category="在庫最適化",
    tool_name="optimize_ss_policy",
    description="(s,S)発注方策の最適化",
    arguments={
        "mu": 100,
        "sigma": 15,
        "lead_time": 5,
        "holding_cost": 1,
        "stockout_cost": 100,
        "fixed_cost": 500,
        "n_samples": 50,
        "n_periods": 200
    }
)

print("\n✓ Category 1 tests completed")

# Save results
output_file = "/Users/kazuhiro/Documents/2510/langflow-mcp/test_results_part1.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "category": "在庫最適化（4ツール）",
        "total_tests": len(test_results),
        "passed": sum(1 for r in test_results if r["success"]),
        "failed": sum(1 for r in test_results if not r["success"]),
        "results": test_results
    }, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"Test results saved to: {output_file}")
print(f"Total tests: {len(test_results)}")
print(f"Passed: {sum(1 for r in test_results if r['success'])}")
print(f"Failed: {sum(1 for r in test_results if not r['success'])}")
print(f"{'='*60}")

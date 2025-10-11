"""
包括的テスト（バグ修正後）- すべてのパラメータ名を修正
全24個のMCPツール（可視化以外）から代表的なツールをテスト
"""
import sys
sys.path.append('.')

from mcp_tools import execute_mcp_function
import json
from datetime import datetime
import numpy as np

test_results = []

def test_function(category, tool_name, description, arguments, expected_status="success"):
    """MCPツールをテストして結果を記録"""
    print(f"\n{'='*60}")
    print(f"Testing: {tool_name}")
    print(f"Category: {category}")
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

        if success:
            print(f"✓ Test PASSED")
            for key in ["best_cost", "optimal_Q", "optimal_R", "optimal_s", "optimal_S",
                       "safety_stock", "reorder_point", "cost", "total_cost", "forecast", "average_cost"]:
                if key in result:
                    test_result["result_summary"][key] = result[key]
                    if isinstance(result[key], (int, float)):
                        print(f"  {key}: {result[key]:.2f}")
                    else:
                        print(f"  {key}: {str(result[key])[:50]}...")
        else:
            print(f"✗ Test FAILED: {result.get('message', 'Unknown error')[:100]}")
            test_result["error_message"] = result.get("message", "Unknown error")[:200]

        test_results.append(test_result)
        return success

    except Exception as e:
        print(f"✗ Test EXCEPTION: {str(e)[:100]}")
        test_results.append({
            "category": category,
            "tool_name": tool_name,
            "description": description,
            "status": "exception",
            "success": False,
            "error_message": str(e)[:200]
        })
        return False


print("\n" + "="*60)
print("Category 1: 在庫最適化（4ツール）")
print("="*60)

test_function("在庫最適化", "calculate_safety_stock", "安全在庫の計算",
    {"average_demand": 100, "demand_std": 15, "lead_time": 7, "service_level": 0.95})

test_function("在庫最適化", "optimize_ss_policy", "(s,S)発注方策の最適化",
    {"mu": 100, "sigma": 15, "lead_time": 5, "holding_cost": 1, "stockout_cost": 100, "fixed_cost": 500, "n_samples": 30, "n_periods": 100})

test_function("在庫最適化", "optimize_periodic_inventory", "定期発注方策の最適化（Adam）",
    {
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
        "max_iter": 30,
        "n_samples": 10,
        "n_periods": 50,
        "algorithm": "adam"
    })

test_function("在庫最適化", "optimize_safety_stock_allocation", "タブーサーチによる安全在庫配置",
    {
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
        "max_iter": 50,
        "tabu_tenure": 5
    })

print("\n" + "="*60)
print("Category 2: シミュレーション（6ツール）")
print("="*60)

test_function("シミュレーション", "simulate_qr_policy", "(Q,R)方策のシミュレーション",
    {"Q": 200, "R": 600, "mu": 100, "sigma": 15, "lead_time": 5, "holding_cost": 1, "stockout_cost": 100, "fixed_cost": 500, "n_samples": 30, "n_periods": 100})

# 修正: S → base_stock_level
test_function("シミュレーション", "simulate_base_stock_policy", "基在庫方策のシミュレーション",
    {"base_stock_level": 150, "mu": 100, "sigma": 15, "lead_time": 5, "holding_cost": 1, "stockout_cost": 100, "n_samples": 30, "n_periods": 100})

print("\n" + "="*60)
print("Category 3: 発注方策の最適化（4ツール）")
print("="*60)

test_function("発注方策", "optimize_qr_policy", "(Q,R)方策の最適化",
    {"mu": 100, "sigma": 15, "lead_time": 5, "holding_cost": 1, "stockout_cost": 100, "fixed_cost": 500, "n_samples": 30, "n_periods": 100})

print("\n" + "="*60)
print("Category 4: 需要予測と分析（4ツール）")
print("="*60)

# 需要データを生成
np.random.seed(42)
demand_data = np.random.normal(100, 15, 200).tolist()

# 修正: demand_data → demand_history
test_function("需要予測", "forecast_demand", "需要予測（移動平均）",
    {"demand_history": demand_data, "method": "moving_average", "window": 7, "forecast_periods": 10})

# 修正: demand_data → demand
test_function("需要予測", "analyze_demand_pattern", "需要パターン分析",
    {"demand": demand_data})

print("\n" + "="*60)
print("Category 5: EOQ計算（2ツール）")
print("="*60)

# 修正: calculate_eoq_basic_raw → calculate_eoq_raw
test_function("EOQ", "calculate_eoq_raw", "基本EOQ計算",
    {"K": 500, "d": 100, "h": 1, "b": 0, "r": 0, "c": 0, "theta": 0})

# 修正: calculate_eoq_backorder_raw → calculate_eoq_raw (with b>0)
test_function("EOQ", "calculate_eoq_raw", "バックオーダー対応EOQ",
    {"K": 500, "d": 100, "h": 1, "b": 100, "r": 0, "c": 0, "theta": 0})

print("\n" + "="*60)
print("Category 6: Wagner-Whitinアルゴリズム（1ツール）")
print("="*60)

test_function("Wagner-Whitin", "calculate_wagner_whitin", "動的発注計画",
    {"demand": [100, 120, 80, 150, 90], "fixed_cost": 500, "holding_cost": 1})

print("\n" + "="*60)
print("Category 7-9: その他のツール")
print("="*60)

# 修正: 最終製品に正の需要を設定
test_function("ネットワーク分析", "analyze_inventory_network", "サプライチェーンネットワーク分析",
    {
        "items_data": json.dumps([
            {"name": "原材料", "h": 1.0, "b": 50.0, "average_demand": 0, "std_demand": 0, "lead_time": 2.0},
            {"name": "製品", "h": 5.0, "b": 150.0, "average_demand": 100.0, "std_demand": 20.0, "lead_time": 1.0}
        ]),
        "bom_data": json.dumps([{"child": "原材料", "parent": "製品", "units": 1.0}])
    })

test_function("ポリシー比較", "compare_inventory_policies", "在庫方策の比較",
    {"mu": 100, "sigma": 15, "lead_time": 5, "holding_cost": 1, "stockout_cost": 100, "fixed_cost": 500, "n_samples": 30, "n_periods": 100})

# 結果集計
print("\n" + "="*60)
print("Test Summary")
print("="*60)

total = len(test_results)
passed = sum(1 for r in test_results if r["success"])
failed = total - passed

print(f"Total tests: {total}")
print(f"Passed: {passed} ({passed/total*100:.1f}%)")
print(f"Failed: {failed} ({failed/total*100:.1f}%)")
print()

# カテゴリ別集計
categories = {}
for r in test_results:
    cat = r["category"]
    if cat not in categories:
        categories[cat] = {"total": 0, "passed": 0}
    categories[cat]["total"] += 1
    if r["success"]:
        categories[cat]["passed"] += 1

print("Category Summary:")
for cat, stats in categories.items():
    status = "✅" if stats['passed'] == stats['total'] else ("🟡" if stats['passed'] > 0 else "❌")
    print(f"  {status} {cat}: {stats['passed']}/{stats['total']} passed")

# Save results
output_file = "/Users/kazuhiro/Documents/2510/langflow-mcp/test_results_fixed.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed/total*100:.1f}%",
        "categories": categories,
        "results": test_results
    }, f, ensure_ascii=False, indent=2)

print(f"\nResults saved to: {output_file}")

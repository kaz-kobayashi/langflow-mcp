"""
Phase 8: 安全在庫配置ネットワーク可視化のテスト
"""
from mcp_tools import execute_mcp_function
import json


def test_visualize_safety_stock_network():
    """
    安全在庫配置ネットワークの可視化テスト
    """
    print("\n" + "=" * 60)
    print("Test 1: optimize_safety_stock_allocation + visualize_safety_stock_network")
    print("=" * 60)

    # 安全在庫配置最適化用のデータ
    items = [
        {
            "name": "サプライヤーA",
            "process_time": 1,
            "max_service_time": 3,
            "avg_demand": 0,
            "demand_std": 0,
            "holding_cost": 1,
            "stockout_cost": 10,
            "fixed_cost": 1000,
            "x": 0,
            "y": 0
        },
        {
            "name": "工場",
            "process_time": 1,
            "max_service_time": 2,
            "avg_demand": 0,
            "demand_std": 0,
            "holding_cost": 2,
            "stockout_cost": 20,
            "fixed_cost": 2000,
            "x": 1,
            "y": 0
        },
        {
            "name": "製品",
            "process_time": 1,
            "max_service_time": 1,
            "avg_demand": 100,
            "demand_std": 20,
            "holding_cost": 5,
            "stockout_cost": 100,
            "fixed_cost": 5000,
            "x": 2,
            "y": 0
        }
    ]

    bom = [
        {"child": "サプライヤーA", "parent": "工場", "quantity": 1},
        {"child": "工場", "parent": "製品", "quantity": 1}
    ]

    print("\nStep 1: 安全在庫配置最適化を実行...")
    opt_result = execute_mcp_function("optimize_safety_stock_allocation", {
        "items_data": json.dumps(items),
        "bom_data": json.dumps(bom)
    })

    print(f"Status: {opt_result['status']}")
    if opt_result['status'] == 'success':
        print(f"✅ 最適化成功!")
        print(f"  総安全在庫コスト: {opt_result['total_cost']:.2f}")
        print(f"\n  各ステージの結果:")
        for result in opt_result['optimization_results']:
            node_idx = result['node']
            item_name = items[node_idx]['name'] if node_idx < len(items) else f"Node {node_idx}"
            print(f"    {item_name}: 安全在庫={result['safety_stock']:.2f}, リードタイム={result['lead_time']:.2f}")
    else:
        print(f"❌ Error: {opt_result['message']}")
        return None

    print("\nStep 2: ネットワーク可視化を実行...")
    viz_result = execute_mcp_function("visualize_safety_stock_network", {
        "optimization_result": opt_result
    })

    print(f"\nStatus: {viz_result['status']}")
    if viz_result['status'] == 'success':
        print(f"✅ 可視化成功!")
        print(f"  可視化ID: {viz_result['visualization_id']}")
        print(f"\n  ネットワークサマリー:")
        summary = viz_result['network_summary']
        print(f"    ステージ数: {summary['num_stages']}")
        print(f"    接続数: {summary['num_connections']}")
        print(f"    総安全在庫: {summary['total_safety_stock']:.2f}")
        print(f"    平均リードタイム: {summary['avg_lead_time']:.2f}")
        return viz_result
    else:
        print(f"❌ Error: {viz_result['message']}")
        return None


def test_complex_network_visualization():
    """
    複雑なネットワークの可視化テスト（4段階）
    """
    print("\n" + "=" * 60)
    print("Test 2: 複雑なネットワーク（4段階）の可視化")
    print("=" * 60)

    items = [
        {
            "name": "原材料A",
            "process_time": 1,
            "max_service_time": 4,
            "avg_demand": 0,
            "demand_std": 0,
            "holding_cost": 0.5,
            "stockout_cost": 5,
            "fixed_cost": 500,
            "x": 0,
            "y": 1
        },
        {
            "name": "原材料B",
            "process_time": 1,
            "max_service_time": 3,
            "avg_demand": 0,
            "demand_std": 0,
            "holding_cost": 0.8,
            "stockout_cost": 8,
            "fixed_cost": 800,
            "x": 0,
            "y": -1
        },
        {
            "name": "部品",
            "process_time": 1,
            "max_service_time": 2,
            "avg_demand": 0,
            "demand_std": 0,
            "holding_cost": 2,
            "stockout_cost": 20,
            "fixed_cost": 2000,
            "x": 1,
            "y": 0
        },
        {
            "name": "最終製品",
            "process_time": 1,
            "max_service_time": 1,
            "avg_demand": 150,
            "demand_std": 30,
            "holding_cost": 8,
            "stockout_cost": 200,
            "fixed_cost": 10000,
            "x": 2,
            "y": 0
        }
    ]

    bom = [
        {"child": "原材料A", "parent": "部品", "quantity": 1},
        {"child": "原材料B", "parent": "部品", "quantity": 2},
        {"child": "部品", "parent": "最終製品", "quantity": 1}
    ]

    print("\nStep 1: 安全在庫配置最適化...")
    opt_result = execute_mcp_function("optimize_safety_stock_allocation", {
        "items_data": json.dumps(items),
        "bom_data": json.dumps(bom)
    })

    print(f"Status: {opt_result['status']}")
    if opt_result['status'] == 'success':
        print(f"✅ 最適化成功!")
        print(f"  総安全在庫コスト: {opt_result['total_cost']:.2f}")
    else:
        print(f"❌ Error: {opt_result['message']}")
        return

    print("\nStep 2: ネットワーク可視化...")
    viz_result = execute_mcp_function("visualize_safety_stock_network", {
        "optimization_result": opt_result
    })

    print(f"\nStatus: {viz_result['status']}")
    if viz_result['status'] == 'success':
        print(f"✅ 可視化成功!")
        print(f"  可視化ID: {viz_result['visualization_id']}")
    else:
        print(f"❌ Error: {viz_result['message']}")


def test_error_handling():
    """
    エラーハンドリングのテスト
    """
    print("\n" + "=" * 60)
    print("Test 3: エラーハンドリング（不正な最適化結果）")
    print("=" * 60)

    # 不正な最適化結果
    invalid_result = {
        "status": "error",
        "message": "テスト用エラー"
    }

    result = execute_mcp_function("visualize_safety_stock_network", {
        "optimization_result": invalid_result
    })

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'error':
        print(f"✅ エラーが適切に処理されました")
        print(f"  エラーメッセージ: {result['message']}")
    else:
        print(f"❌ エラーが検出されませんでした")


if __name__ == "__main__":
    print("Phase 8: 安全在庫配置ネットワーク可視化のテスト開始")
    print("=" * 60)

    # Test 1: 基本的なネットワーク可視化
    test_visualize_safety_stock_network()

    # Test 2: 複雑なネットワーク
    test_complex_network_visualization()

    # Test 3: エラーハンドリング
    test_error_handling()

    print("\n" + "=" * 60)
    print("All Phase 8 tests completed!")
    print("=" * 60)

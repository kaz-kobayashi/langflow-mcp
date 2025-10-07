"""
Phase 7: 定期発注最適化機能のテスト
"""
import json
from mcp_tools import execute_mcp_function


def test_optimize_periodic_inventory():
    """
    定期発注最適化のテスト
    """
    print("\n" + "=" * 60)
    print("Test 1: optimize_periodic_inventory (2段階サプライチェーン)")
    print("=" * 60)

    # シンプルな2段階サプライチェーン
    network_data = {
        "stages": [
            {
                "name": "原材料",
                "average_demand": 0,
                "sigma": 0,
                "h": 1,
                "b": 10,
                "z": 1.65,
                "capacity": 1000,
                "net_replenishment_time": 2,
                "x": 0,
                "y": 0
            },
            {
                "name": "製品",
                "average_demand": 100,
                "sigma": 20,
                "h": 2,
                "b": 50,
                "z": 1.65,
                "capacity": 1000,
                "net_replenishment_time": 1,
                "x": 1,
                "y": 0
            }
        ],
        "connections": [
            {
                "child": "原材料",
                "parent": "製品",
                "units": 1,
                "allocation": 1.0
            }
        ]
    }

    result = execute_mcp_function("optimize_periodic_inventory", {
        "network_data": network_data,
        "max_iter": 50,
        "n_samples": 10,
        "n_periods": 100,
        "learning_rate": 1.0
    })

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"✅ 最適化成功!")
        print(f"  最終コスト: {result['best_cost']:.2f}")
        print(f"  収束: {result['converged']}")
        print(f"  反復回数: {result['iterations']}")
        print(f"\n  各ステージの基在庫レベル:")
        for stage in result['stages']:
            print(f"    {stage['name']}: 基在庫={stage['base_stock_level']:.2f}, ローカル基在庫={stage['local_base_stock_level']:.2f}")
        return result
    else:
        print(f"❌ Error: {result['message']}")
        return None


def test_visualize_periodic_optimization(opt_result):
    """
    定期発注最適化の可視化テスト
    """
    if opt_result is None:
        print("\n最適化結果がないため、可視化テストをスキップ")
        return

    print("\n" + "=" * 60)
    print("Test 2: visualize_periodic_optimization")
    print("=" * 60)

    result = execute_mcp_function("visualize_periodic_optimization", {
        "optimization_result": opt_result
    })

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"✅ 可視化成功!")
        print(f"  コストグラフID: {result['cost_chart_id']}")
        print(f"  勾配グラフID: {result['gradient_chart_id']}")
        print(f"\n  サマリー:")
        summary = result['summary']
        print(f"    初期コスト: {summary['initial_cost']:.2f}")
        print(f"    最終コスト: {summary['final_cost']:.2f}")
        print(f"    コスト削減: {summary['cost_reduction']:.2f}")
        print(f"    反復回数: {summary['iterations']}")
        print(f"    収束: {summary['converged']}")
    else:
        print(f"❌ Error: {result['message']}")


def test_complex_network():
    """
    複雑なネットワークでのテスト（3段階）
    """
    print("\n" + "=" * 60)
    print("Test 3: optimize_periodic_inventory (3段階サプライチェーン)")
    print("=" * 60)

    network_data = {
        "stages": [
            {
                "name": "サプライヤー",
                "average_demand": 0,
                "sigma": 0,
                "h": 0.5,
                "b": 5,
                "z": 1.65,
                "capacity": 2000,
                "net_replenishment_time": 3,
                "x": 0,
                "y": 0
            },
            {
                "name": "工場",
                "average_demand": 0,
                "sigma": 0,
                "h": 1,
                "b": 15,
                "z": 1.65,
                "capacity": 1500,
                "net_replenishment_time": 2,
                "x": 1,
                "y": 0
            },
            {
                "name": "製品",
                "average_demand": 150,
                "sigma": 30,
                "h": 3,
                "b": 80,
                "z": 1.65,
                "capacity": 1000,
                "net_replenishment_time": 1,
                "x": 2,
                "y": 0
            }
        ],
        "connections": [
            {
                "child": "サプライヤー",
                "parent": "工場",
                "units": 1,
                "allocation": 1.0
            },
            {
                "child": "工場",
                "parent": "製品",
                "units": 1,
                "allocation": 1.0
            }
        ]
    }

    result = execute_mcp_function("optimize_periodic_inventory", {
        "network_data": network_data,
        "max_iter": 100,
        "n_samples": 20,
        "n_periods": 200,
        "learning_rate": 0.8
    })

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"✅ 最適化成功!")
        print(f"  最終コスト: {result['best_cost']:.2f}")
        print(f"  収束: {result['converged']}")
        print(f"  反復回数: {result['iterations']}")
        print(f"\n  各ステージの基在庫レベル:")
        for stage in result['stages']:
            print(f"    {stage['name']}: 基在庫={stage['base_stock_level']:.2f}")
    else:
        print(f"❌ Error: {result['message']}")


def test_error_handling():
    """
    エラーハンドリングのテスト
    """
    print("\n" + "=" * 60)
    print("Test 4: エラーハンドリング（不正なデータ）")
    print("=" * 60)

    # 必須フィールド不足
    invalid_network = {
        "stages": [
            {
                "name": "製品",
                "average_demand": 100
                # 他の必須フィールドが不足
            }
        ],
        "connections": []
    }

    result = execute_mcp_function("optimize_periodic_inventory", {
        "network_data": invalid_network
    })

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'error':
        print(f"✅ エラーが適切に処理されました")
        print(f"  エラーメッセージ: {result['message']}")
    else:
        print(f"❌ エラーが検出されませんでした")


if __name__ == "__main__":
    print("Phase 7: 定期発注最適化機能のテスト開始")
    print("=" * 60)

    # Test 1: 基本的な最適化
    opt_result = test_optimize_periodic_inventory()

    # Test 2: 可視化
    test_visualize_periodic_optimization(opt_result)

    # Test 3: 複雑なネットワーク
    test_complex_network()

    # Test 4: エラーハンドリング
    test_error_handling()

    print("\n" + "=" * 60)
    print("All Phase 7 tests completed!")
    print("=" * 60)

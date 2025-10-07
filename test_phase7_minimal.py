"""
Phase 7: 最小限のデータでのテスト（z, x, y なし）
"""
from mcp_tools import execute_mcp_function


def test_minimal_data():
    """
    最小限の必須フィールドのみでテスト
    """
    print("\n" + "=" * 60)
    print("Test: 最小限データ（z, x, y なし）")
    print("=" * 60)

    # z, x, y を含まない最小限のデータ
    network_data = {
        "stages": [
            {
                "name": "原材料",
                "average_demand": 0,
                "sigma": 0,
                "h": 1,
                "b": 10,
                "capacity": 1000,
                "net_replenishment_time": 2
            },
            {
                "name": "製品",
                "average_demand": 100,
                "sigma": 20,
                "h": 2,
                "b": 50,
                "capacity": 1000,
                "net_replenishment_time": 1
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
        "max_iter": 10,
        "n_samples": 5,
        "n_periods": 50
    })

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"✅ 最適化成功!")
        print(f"  最終コスト: {result['best_cost']:.2f}")
        print(f"  反復回数: {result['iterations']}")
        print(f"\n  各ステージの基在庫レベル:")
        for stage in result['stages']:
            print(f"    {stage['name']}: 基在庫={stage['base_stock_level']:.2f}")
            if 'z' in stage:
                print(f"      安全係数(自動計算): {stage['z']:.3f}")
    else:
        print(f"❌ Error: {result['message']}")


if __name__ == "__main__":
    test_minimal_data()
